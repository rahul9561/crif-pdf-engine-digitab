"""Example Django views for crif-pdf-engine.

Install in your Django project:   pip install "crif-pdf-engine @ git+https://<your-git-host>/crifs-digitab.git"
The engine has no Django dependency; this file only shows how to wire it up.

    # urls.py
    from django.urls import path
    from .views import crif_report_pdf, crif_report_pdf_from_request

    urlpatterns = [
        path("reports/<int:pk>/crif.pdf", crif_report_pdf, name="crif-report-pdf"),
        path("reports/crif/render/", crif_report_pdf_from_request, name="crif-report-render"),
    ]
"""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from crif_pdf_engine import CrifReportError, render_pdf, suggested_filename

# from .models import CreditReport   # your model that stores the Digitap JSON response


def _pdf_response(json_data, *, inline: bool = True) -> HttpResponse:
    """Render and wrap in an HttpResponse with a "<name>_<report id>.pdf" filename."""
    pdf_bytes = render_pdf(json_data)
    filename = suggested_filename(json_data)  # e.g. CRIF_ANAND_VARDHAN_GOYAL_CCR261006CR581766645.pdf
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response


@login_required
@require_GET
def crif_report_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """GET /reports/<pk>/crif.pdf[?download=1] — render a stored report."""
    report = get_object_or_404(CreditReport, pk=pk, owner=request.user)  # noqa: F821
    json_data = report.raw_response  # dict from a JSONField (a JSON string also works)
    try:
        return _pdf_response(json_data, inline=request.GET.get("download") != "1")
    except CrifReportError as exc:
        return HttpResponseBadRequest(f"Cannot render CRIF report: {exc}")


@login_required
@require_POST
def crif_report_pdf_from_request(request: HttpRequest) -> HttpResponse:
    """POST raw Digitap JSON in the body; returns the PDF as a download."""
    try:
        json_data = json.loads(request.body)
        return _pdf_response(json_data, inline=False)
    except (ValueError, CrifReportError) as exc:  # json.JSONDecodeError is a ValueError
        return HttpResponseBadRequest(f"Cannot render CRIF report: {exc}")


# ---------------------------------------------------------------------------
# Large reports: render in Celery instead of the request/response cycle.
# A 10-account report renders in ~3-5 s, a 100-account report in ~30 s.
# ---------------------------------------------------------------------------
#
# from celery import shared_task
# from django.core.files.base import ContentFile
#
# @shared_task
# def build_crif_pdf(report_id: int) -> None:
#     report = CreditReport.objects.get(pk=report_id)
#     pdf_bytes = render_pdf(report.raw_response)
#     report.pdf.save(suggested_filename(report.raw_response), ContentFile(pdf_bytes))
