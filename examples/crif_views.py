import logging
from datetime import date, datetime

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from crif_pdf_engine_digitap import render_pdf, suggested_filename
from accounts.middleware import ApiKeyAuthentication

from agentplans.models import ActivePlan, ApiService, ApiUsage, PlanApiPricing
from cibil.models import CibilReport
from wallet.models import Wallet, WalletLedger, WalletTransaction

from .prefill_crifs import (
    MANUAL_FIELDS,
    CRIFClient,
    DigitapAPIError,
    MobilePrefillClient,
    prefill_to_crif_fields,
)
from ..serializers import CRIFReportSerializer, MobilePrefillSerializer

logger = logging.getLogger("digitap.crif")

# Must match ApiService.code in admin (agentplans > Api services)
CRIF_SERVICE_CODE = "crif"

# Fixed by backend; whatever the frontend sends for these keys is ignored.
CRIF_FIXED_FIELDS = {
    "consent": True,
    "prefill_lookup": "0",
    "report_type": "1",
}

# Key in ApiUsage.request_data holding the gender the user typed (for PDF regeneration).
USER_GENDER_KEY = "user_gender"


def crif_request_data(request):
    """Frontend sends only customer details; backend adds the fixed fields."""
    data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
    data.update(CRIF_FIXED_FIELDS)
    return data

CRIF_MESSAGES = {
    101: "CRIF report fetched successfully",
    102: "No record found in credit bureau",
    103: "Name not found against mobile number",
}
PREFILL_MESSAGES = {
    101: "Details fetched successfully",
    102: "No record found for this mobile number",
    103: "Name not found against mobile number",
}


class BillingError(Exception):
    """Raised when the user can't be charged for CRIF (no plan, no price, low balance)."""

    def __init__(self, message, http_status=status.HTTP_403_FORBIDDEN):
        super().__init__(message)
        self.http_status = http_status


def error_response(e, request, service):
    logger.error("%s failed user=%s http=%s request_id=%s body=%s",
                 service, request.user.pk, e.http_status, e.request_id, e.body)
    if e.http_status in (400, 403):
        return Response({"success": False, "message": str(e), "request_id": e.request_id},
                        status=status.HTTP_400_BAD_REQUEST)
    if e.http_status == 503:
        return Response({"success": False, "message": "Source is busy. Please try again later.",
                         "request_id": e.request_id},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    # 401 / 500 / network -> our side; never return 401 to frontend (logs agent out)
    return Response({"success": False, "message": "%s service unavailable. Please try again later." % service,
                     "request_id": e.request_id},
                    status=status.HTTP_502_BAD_GATEWAY)


def clean_gender(value):
    """User-entered gender as a stripped string, or None if blank."""
    text = str(value).strip() if value is not None else ""
    return text or None


def user_gender_from_request(request, validated):
    """Gender the user sent; serializer value first, then the raw request body."""
    return clean_gender(validated.get("gender")) or clean_gender(request.data.get("gender"))


def build_crif_pdf(report_json, gender=None):
    """report_json (or the whole CRIF API response) -> (pdf_bytes, filename).

    gender: user-entered gender; always wins over the report JSON's gender.
    None / blank -> the gender in the report JSON is used.
    """
    return render_pdf(report_json, gender=gender), suggested_filename(report_json)


def parse_dob(value):
    """Accepts the date formats Digitap/CRIF commonly use; returns None if unknown."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d%m%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def customer_name(d):
    if d.get("name"):
        return d["name"]
    parts = [d.get("first_name"), d.get("middle_name"), d.get("last_name")]
    return " ".join(p for p in parts if p).strip() or "-"


def file_url(request, field_file):
    """Signed S3 URL with django-storages; absolute URL for local media."""
    url = field_file.url
    return request.build_absolute_uri(url) if url.startswith("/") else url


def json_safe(d):
    """validated_data may hold date objects; make it JSONField-safe."""
    return {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in d.items()}


def get_crif_price(user):
    """
    -> (api_service, price) for this user's active plan.
    Raises BillingError if the service is off, user has no plan, CRIF isn't in the plan,
    or the wallet can't cover one hit.
    """
    api_service = ApiService.objects.filter(
        code=CRIF_SERVICE_CODE, is_active=True, status=ApiService.Status.ACTIVE
    ).first()
    if not api_service:
        raise BillingError("CRIF service is currently not available.",
                           status.HTTP_503_SERVICE_UNAVAILABLE)

    active = ActivePlan.objects.select_related("plan").filter(user=user).first()
    if not active:
        raise BillingError("No active plan. Please recharge to use CRIF report.")

    pricing = PlanApiPricing.objects.filter(plan=active.plan, api_service=api_service).first()
    if not pricing:
        raise BillingError("CRIF report is not included in your plan.")

    wallet, _ = Wallet.objects.get_or_create(user=user)
    if wallet.balance < pricing.price:
        raise BillingError("Insufficient wallet balance. CRIF report costs Rs %s." % pricing.price,
                           status.HTTP_402_PAYMENT_REQUIRED)

    return api_service, pricing.price


def debit_wallet(user, amount, reference_id, service, narration):
    """
    Debit the wallet atomically: lock wallet row -> check balance -> WalletTransaction
    + WalletLedger -> new balance. reference_id is unique, so the same report can
    never be charged twice (IntegrityError). Call inside transaction.atomic().
    """
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if wallet.balance < amount:
        raise BillingError("Insufficient wallet balance.", status.HTTP_402_PAYMENT_REQUIRED)

    opening = wallet.balance
    closing = opening - amount

    txn = WalletTransaction.objects.create(
        user=user,
        reference_id=reference_id,
        amount=amount,
        txn_type=WalletTransaction.TxnType.DEBIT,
        service=service,
        narration=narration[:255],
        status="success",
    )
    WalletLedger.objects.create(
        wallet=wallet,
        transaction=txn,
        opening_balance=opening,
        amount=amount,
        closing_balance=closing,
        entry_type="debit",
    )
    wallet.balance = closing
    wallet.save(update_fields=["balance", "updated_at"])
    return txn


class CRIFCreditReportAPIView(APIView):
    """
    prefill_lookup "1": we call Mobile to Prefill ourselves, then CRIF with prefill_lookup "0".
    prefill_lookup "0": customer details come from the request.

    Billing: price comes from the user's ActivePlan -> PlanApiPricing for ApiService "crif".
    Wallet is debited per hit, only when the bureau returns a report (result_code 101).
    Every CRIF call is saved as CibilReport + ApiUsage; on success the response carries
    report_json and our own PDF link (report_pdf_url).

    Gender: if the request carries a non-blank "gender", the PDF shows it (the bureau
    JSON's gender can be wrong). Otherwise the PDF uses the gender from the JSON.
    """
    # permission_classes = [IsAuthenticated]
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request):
        # Frontend sends: mobile_no, pan, first_name, last_name (+ optional gender)
        s = CRIFReportSerializer(data=crif_request_data(request))
        if not s.is_valid():
            return Response({"success": False, "message": "Invalid input", "errors": s.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # Check plan/price/balance BEFORE spending anything at Digitap (prefill or CRIF)
        try:
            api_service, price = get_crif_price(request.user)
        except BillingError as e:
            return Response({"success": False, "message": str(e)}, status=e.http_status)

        d = dict(s.validated_data)
        d.pop("consent")
        # Captured before prefill (d.update below) can overwrite it.
        user_gender = user_gender_from_request(request, d)
        prefill_info = None

        if d["prefill_lookup"] == "1":
            try:
                pre = MobilePrefillClient().fetch(d["mobile"])
            except DigitapAPIError as e:
                return error_response(e, request, "Prefill")

            pre_code = pre.get("result_code")
            prefill_info = {"result_code": pre_code, "request_id": pre.get("request_id"),
                            "billable": pre_code == 101}
            if pre_code != 101:
                return Response({
                    "success": False,
                    "require_details": True,
                    "message": PREFILL_MESSAGES.get(pre_code, "Could not fetch details") +
                               ". Please enter customer details.",
                    "prefill": prefill_info,
                }, status=status.HTTP_200_OK)

            fields = prefill_to_crif_fields(pre.get("result"))
            missing = [f for f in MANUAL_FIELDS if not fields.get(f)]
            if missing:
                # let agent complete the form with what we already got
                return Response({
                    "success": False,
                    "require_details": True,
                    "message": "Some customer details are missing. Please complete them.",
                    "missing_fields": missing,
                    "crif_fields": fields,
                    "prefill": prefill_info,
                }, status=status.HTTP_200_OK)

            d.update(fields)
            d["prefill_lookup"] = "0"

        # Record the attempt before calling the bureau, so every hit is traceable.
        record = CibilReport.objects.create(
            user=request.user,
            api_service=api_service,
            report_type="crif",
            status="pending",
            price=price,
            name=customer_name(d),
            mobile=str(d.get("mobile") or "")[:15],
            pan=(d.get("pan_number") or None),
            # pan=(d.get("pan") or None),
            dob=parse_dob(d.get("dob") or d.get("date_of_birth")),
        )
        usage = ApiUsage.objects.create(
            user=request.user,
            api_service=api_service,
            price=price,
            reference_id=str(record.request_id),   # unique per hit -> no double charge
            request_data={**json_safe(d), USER_GENDER_KEY: user_gender},
            status="pending",
        )

        try:
            result = CRIFClient().get_credit_report(**d)
        except DigitapAPIError as e:
            record.status = "failed"
            record.error_message = str(e)
            record.error_response = e.body if isinstance(e.body, (dict, list)) else {"body": str(e.body)}
            record.save(update_fields=["status", "error_message", "error_response"])
            usage.status = "failed"
            usage.response_data = {"http_status": e.http_status, "request_id": e.request_id,
                                   "message": str(e)}
            usage.save(update_fields=["status", "response_data"])
            return error_response(e, request, "CRIF")

        code = result.get("result_code")
        message = CRIF_MESSAGES.get(code, result.get("message", "CRIF request failed"))
        record.response = result
        usage.response_data = {"result_code": code, "request_id": result.get("request_id"),
                               "client_ref_num": result.get("client_ref_num")}

        payload = {
            "success": code == 101,
            "billable": code == 101,
            "result_code": code,
            "message": message,
            "report_id": str(record.id),
            "request_id": result.get("request_id"),
            "client_ref_num": result.get("client_ref_num"),
            "prefill": prefill_info,
            "charged": None,
        }

        if code != 101:
            # no report -> no charge
            record.status = "failed"
            record.error_message = message
            record.save(update_fields=["status", "error_message", "response"])
            usage.status = "failed"
            usage.save(update_fields=["status", "response_data"])
            return Response(payload, status=status.HTTP_200_OK)

        # ---- charge per hit (report received) ----
        try:
            with transaction.atomic():
                txn = debit_wallet(
                    user=request.user,
                    amount=price,
                    reference_id="CRIF-%s" % record.request_id,
                    service="crif",
                    narration="CRIF report %s (%s)" % (record.name, result.get("request_id")),
                )
                usage.status = "success"
                usage.response_data["wallet_txn"] = txn.reference_id
                usage.save(update_fields=["status", "response_data"])
            payload["charged"] = str(price)
            payload["wallet_txn"] = txn.reference_id
        except IntegrityError:
            logger.warning("CRIF already charged report=%s", record.id)
        except BillingError as e:
            # balance dropped between pre-check and now (parallel hits)
            logger.error("CRIF debit refused user=%s report=%s: %s", request.user.pk, record.id, e)
            usage.status = "failed"
            usage.response_data = {**usage.response_data, "billing_error": str(e)}
            usage.save(update_fields=["status", "response_data"])
        except Exception:
            # report is already bought from bureau; don't hide it from the agent,
            # but flag the usage so it can be recovered from admin
            logger.exception("CRIF wallet debit FAILED user=%s report=%s price=%s",
                             request.user.pk, record.id, price)
            usage.status = "failed"
            usage.response_data = {**usage.response_data, "billing_error": "wallet debit failed"}
            usage.save(update_fields=["status", "response_data"])

        # ---- report JSON + our PDF ----
        res = result.get("result") or {}
        report_json = res.get("result_json") or None
        record.status = "success"
        record.xaler_pdf_report = res.get("result_pdf") or None  # Digitap's S3 PDF (expires ~1 hr)

        payload["data"] = {
            "report_pdf_url": None,                  # our engine's PDF, stored on the record
            "report_json": report_json,
            "report_pdf_filename": None,
            "digitap_pdf_url": record.xaler_pdf_report,
        }

        if report_json:
            try:
                pdf_bytes, filename = build_crif_pdf(report_json, gender=user_gender)
                record.report_pdf.save(filename, ContentFile(pdf_bytes), save=False)
                payload["data"]["report_pdf_filename"] = filename
            except Exception:
                # never lose a paid report because the PDF failed
                logger.exception("CRIF PDF render/save failed user=%s report=%s",
                                 request.user.pk, record.id)

        record.save()

        if record.report_pdf:
            payload["data"]["report_pdf_url"] = file_url(request, record.report_pdf)

        return Response(payload, status=status.HTTP_200_OK)


def saved_user_gender(record):
    """Gender the user sent with the original CRIF request (from ApiUsage), or None."""
    usage = ApiUsage.objects.filter(reference_id=str(record.request_id)).only("request_data").first()
    return clean_gender(((usage.request_data if usage else None) or {}).get(USER_GENDER_KEY))


class CRIFReportPDFAPIView(APIView):
    """GET a fresh PDF link for a saved CRIF report (signed S3 URLs expire). No charge.

    Optional ?gender=Female re-renders the PDF with that gender (it wins over the JSON).
    """
    # permission_classes = [IsAuthenticated]
    authentication_classes = [ApiKeyAuthentication]

    def get(self, request, report_id):
        record = get_object_or_404(
            CibilReport, id=report_id, user=request.user, report_type="crif", status="success"
        )
        gender_override = clean_gender(request.query_params.get("gender"))

        if not record.report_pdf or gender_override:
            # PDF render failed earlier, or a new gender was given: render from the saved response
            report_json = ((record.response or {}).get("result") or {}).get("result_json")
            if not report_json:
                return Response({"success": False, "message": "PDF not available for this report"},
                                status=status.HTTP_404_NOT_FOUND)
            gender = gender_override or saved_user_gender(record)
            try:
                pdf_bytes, filename = build_crif_pdf(report_json, gender=gender)
                record.report_pdf.save(filename, ContentFile(pdf_bytes), save=True)
            except Exception:
                logger.exception("CRIF PDF regenerate failed report=%s", record.id)
                return Response({"success": False, "message": "Could not generate PDF. Please try again."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "report_id": str(record.id),
            "report_pdf_url": file_url(request, record.report_pdf),
            "report_json": ((record.response or {}).get("result") or {}).get("result_json"),
        })
