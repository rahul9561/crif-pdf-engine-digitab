"""Raw CRIF JSON (validated `B2CReport`) -> plain view-model dict for templates.

ALL business and formatting decisions live here (plus `formatters`). Templates
only iterate and print strings. The view-model contains only str / list / dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence

from . import formatters as fmt
from .models import B2CReport, History, Tradeline

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
#: Perform attributes shown by default (the 9 present in the reference PDF), in order.
DEFAULT_PERFORM_ATTRIBUTES: tuple[str, ...] = (
    "INQUIRIES-IN-LAST-SIX-MONTHS",
    "LENGTH-OF-CREDIT-HISTORY-YEAR",
    "LENGTH-OF-CREDIT-HISTORY-MONTH",
    "AVERAGE-ACCOUNT-AGE-YEAR",
    "AVERAGE-ACCOUNT-AGE-MONTH",
    "NEW-ACCOUNTS-IN-LAST-SIX-MONTHS",
    "NEW-DELINQ-ACCOUNT-IN-LAST-SIX-MONTHS",
    "TOTAL-SECURED-OUTSTANDING",
    "TOTAL-UNSECURED-OUTSTANDING",
)

#: Every known perform attribute: ATTR-NAME -> (display label, kind).
#: kind "amount" = Indian-formatted amount, "raw" = shown as sent.
#: Enable more via ``RenderOptions(perform_attributes=[...])`` or ``"all"``.
PERFORM_ATTRIBUTE_CATALOGUE: dict[str, tuple[str, str]] = {
    "INQUIRIES-IN-LAST-SIX-MONTHS": ("Inquiries In Last Six Months", "raw"),
    "LENGTH-OF-CREDIT-HISTORY-YEAR": ("Length Of Credit History (Years)", "raw"),
    "LENGTH-OF-CREDIT-HISTORY-MONTH": ("Length Of Credit History (Months)", "raw"),
    "AVERAGE-ACCOUNT-AGE-YEAR": ("Average Account Age (Years)", "raw"),
    "AVERAGE-ACCOUNT-AGE-MONTH": ("Average Account Age (Months)", "raw"),
    "NEW-ACCOUNTS-IN-LAST-SIX-MONTHS": ("New Accounts In Last Six Months", "raw"),
    "NEW-DELINQ-ACCOUNT-IN-LAST-SIX-MONTHS": ("New Delinquent Accounts In Last Six Months", "raw"),
    "MAX-DELINQ-INCREASE-12-MONTHS": ("Max Delinq Increase 12 Months", "raw"),
    "TOTAL-DELINQ-INCREASE-12-MONTHS": ("Total Delinq Increase 12 Months", "raw"),
    "MAX-CC-BALANCE-BUILDUP": ("Max CC Balance Buildup", "raw"),
    "CD-TRADES WITHIN-6-MONTHS": ("CD Trades Within 6 Months", "raw"),
    "MAX-TIME-OPEN-TRADE": ("Max Time Open Trade", "raw"),
    "TOTAL-TRADES-GOOD-IN-12-MONTHS": ("Total Trades Good In 12 Months", "raw"),
    "TOTAL-OVERDUE-BUILDUP-SECURED-ACTIVE": ("Total Overdue Buildup Secured Active", "raw"),
    "SCORE-TRANCH-FLIP": ("Score Tranch Flip", "raw"),
    "TOTAL-SECURED-OUTSTANDING": ("Total Secured Outstanding", "amount"),
    "TOTAL-UNSECURED-OUTSTANDING": ("Total Unsecured Outstanding", "amount"),
    "TOTAL-LIVE-SECURED-ACCOUNTS": ("Total Live Secured Accounts", "raw"),
    "TOTAL-OBLIGATIONS": ("Total Obligations", "amount"),
    "TOTAL-SECURED-SANCTION-AMOUNT-OPEN-ACCOUNT": ("Total Secured Sanction Amount Open Account", "amount"),
    "TOTAL-UNSECURED-SANCTION-AMOUNT-OPEN-ACCOUNT": ("Total Unsecured Sanction Amount Open Account", "amount"),
    "TOTAL-CC-SANCTION-AMOUNT-OPEN-ACCOUNT": ("Total CC Sanction Amount Open Account", "amount"),
    "TOTAL-SECURED-SANCTION-AMOUNT-ALL-ACCOUNT": ("Total Secured Sanction Amount All Account", "amount"),
    "TOTAL-UNSECURED-SANCTION-AMOUNT-ALL-ACCOUNT": ("Total Unsecured Sanction Amount All Account", "amount"),
    "TOTAL-CC-OUTSTANDING": ("Total CC Outstanding", "amount"),
    "TOTAL-SECURED-OVER-DUE-ACCOUNTS": ("Total Secured Over Due Accounts", "raw"),
    "TOTAL-UNSECURED-OVER-DUE-ACCOUNTS": ("Total Unsecured Over Due Accounts", "raw"),
    "TOTAL-CC-OVER-DUE-ACCOUNTS": ("Total CC Over Due Accounts", "raw"),
    "TOTAL-SECURED-WORST-DPD-BUCKET-IN-LAST-2-YEARS": ("Total Secured Worst DPD Bucket In Last 2 Years", "raw"),
    "TOTAL-UNSECURED-WORST-DPD-BUCKET-IN-LAST-2-YEARS": ("Total Unsecured Worst DPD Bucket In Last 2 Years", "raw"),
    "TOTAL-SECURED-WORST-DPD-BUCKET-IN-LAST-3-YEARS": ("Total Secured Worst DPD Bucket In Last 3 Years", "raw"),
    "TOTAL-UNSECURED-WORST-DPD-BUCKET-IN-LAST-3-YEARS": ("Total Unsecured Worst DPD Bucket In Last 3 Years", "raw"),
    "TOTAL-SECURED-WORST-DPD-AMOUNT-IN-LAST-2-YEARS": ("Total Secured Worst DPD Amount In Last 2 Years", "amount"),
    "TOTAL-UNSECURED-WORST-DPD-AMOUNT-IN-LAST-2-YEARS": ("Total Unsecured Worst DPD Amount In Last 2 Years", "amount"),
    "TOTAL-CC-WORST-DPD-AMOUNT-IN-LAST-2-YEARS": ("Total CC Worst DPD Amount In Last 2 Years", "amount"),
    "TOTAL-SECURED-WORST-DPD-AMOUNT-IN-LAST-3-YEARS": ("Total Secured Worst DPD Amount In Last 3 Years", "amount"),
    "TOTAL-UNSECURED-WORST-DPD-AMOUNT-IN-LAST-3-YEARS": ("Total Unsecured Worst DPD Amount In Last 3 Years", "amount"),
    "TOTAL-CC-WORST-DPD-AMOUNT-IN-LAST-3-YEARS": ("Total CC Worst DPD Amount In Last 3 Years", "amount"),
    "TOTAL-SUM-OF-ACTIVE-EMI": ("Total Sum Of Active EMI", "amount"),
    "TOTAL-SUM-OF-ACTIVE-SECURED-EMI": ("Total Sum Of Active Secured EMI", "amount"),
    "TOTAL-SUM-OF-ACTIVE-UNSECURED-EMI": ("Total Sum Of Active Unsecured EMI", "amount"),
    "TOTAL-SUM-OF-EMI": ("Total Sum Of EMI", "amount"),
    "TOTAL-SUM-OF-SECURED-EMI": ("Total Sum Of Secured EMI", "amount"),
    "TOTAL-SUM-OF-UNSECURED-EMI": ("Total Sum Of Unsecured EMI", "amount"),
    "MAX-EMI-AMOUNT-ACTIVE": ("Max EMI Amount Active", "amount"),
    "MAX-EMI-AMOUNT": ("Max EMI Amount", "amount"),
    "MAX-SECURED-EMI-AMOUNT": ("Max Secured EMI Amount", "amount"),
    "MAX-UNSECURED-EMI-AMOUNT": ("Max Unsecured EMI Amount", "amount"),
    "MAX-ACTIVE-ACCOUNT-AGE": ("Max Active Account Age", "raw"),
    "MIN-ACTIVE-ACCOUNT-AGE": ("Min Active Account Age", "raw"),
    "MAX-SECURED-ACTIVE-ACCOUNT-AGE": ("Max Secured Active Account Age", "raw"),
    "MIN-SECURED-ACTIVE-ACCOUNT-AGE": ("Min Secured Active Account Age", "raw"),
    "MAX-UNSECURED-ACTIVE-ACCOUNT-AGE": ("Max Unsecured Active Account Age", "raw"),
    "MIN-UNSECURED-ACTIVE-ACCOUNT-AGE": ("Min Unsecured Active Account Age", "raw"),
    "TOTAL-NO-OF-SECURED-INQUIRY-IN-LAST-6-MONTHS": ("Total No Of Secured Inquiry In Last 6 Months", "raw"),
    "TOTAL-NO-OF-UNSECURED-INQUIRY-IN-LAST-6-MONTHS": ("Total No Of Unsecured Inquiry In Last 6 Months", "raw"),
    "NUMBER-OF-LOANS-DELINQUENT-IN-LAST-12-MONTHS": ("Number Of Loans Delinquent In Last 12 Months", "raw"),
    "TOTAL-NO-OF-INQUIRY-IN-LAST-12-MONTHS": ("Total No Of Inquiry In Last 12 Months", "raw"),
    "TOTAL-NO-OF-SECURED-INQUIRY-IN-LAST-12-MONTHS": ("Total No Of Secured Inquiry In Last 12 Months", "raw"),
    "TOTAL-NO-OF-UNSECURED-INQUIRY-IN-LAST-12-MONTHS": ("Total No Of Unsecured Inquiry In Last 12 Months", "raw"),
    "NUMBER-OF-LOANS-DELINQUENT-IN-LAST-24-MONTHS": ("Number Of Loans Delinquent In Last 24 Months", "raw"),
    "TOTAL-NO-OF-INQUIRY-IN-LAST-24-MONTHS": ("Total No Of Inquiry In Last 24 Months", "raw"),
    "TOTAL-NO-OF-SECURED-INQUIRY-IN-LAST-24-MONTHS": ("Total No Of Secured Inquiry In Last 24 Months", "raw"),
    "TOTAL-NO-OF-UNSECURED-INQUIRY-IN-LAST-24-MONTHS": ("Total No Of Unsecured Inquiry In Last 24 Months", "raw"),
    "MAX-OUTSTANDING-AMOUNT-IN-LAST-3-YEARS": ("Max Outstanding Amount In Last 3 Years", "amount"),
    "MAX-SECURED-OUTSTANDING-AMOUNT-IN-LAST-3-YEARS": ("Max Secured Outstanding Amount In Last 3 Years", "amount"),
    "MAX-UNSECURED-OUTSTANDING-AMOUNT-IN-LAST-3-YEARS": ("Max Unsecured Outstanding Amount In Last 3 Years", "amount"),
    "OLDEST-OPEN-CC-MON": ("Oldest Open CC Mon", "raw"),
    "YOUNGEST-OPEN-CC-MON": ("Youngest Open CC Mon", "raw"),
    "TOTAL-CC-SANCTION-AMOUNT-ALL-ACCOUNT": ("Total CC Sanction Amount All Account", "amount"),
    "NUM-INC-BAL-REVOLVING-TRADES-12M": ("Num Inc Bal Revolving Trades 12M", "raw"),
    "MAX-SPEND-CC-UTIL-6M": ("Max Spend CC Util 6M", "raw"),
    "MAX-TIME-CC-ALL-TRADE": ("Max Time CC All Trade", "raw"),
    "ALL-TYPES-TRADES-WRITTEN-OFF": ("All Types Trades Written Off", "raw"),
    "TOTAL-CC-WORST-DPD-BUCKET-IN-LAST-2-YEARS": ("Total CC Worst DPD Bucket In Last 2 Years", "raw"),
    "TOTAL-CC-WORST-DPD-BUCKET-IN-LAST-3-YEARS": ("Total CC Worst DPD Bucket In Last 3 Years", "raw"),
    "TOTAL-P2P-LOAN-AMOUNT-ACTIVE": ("Total P2P Loan Amount Active", "amount"),
    "MAX-P2P-LOAN-AMOUNT-ACTIVE": ("Max P2P Loan Amount Active", "amount"),
    "TOTAL-P2P-ACTIVE-ACCOUNTS": ("Total P2P Active Accounts", "raw"),
    "TOTAL-P2P-ACTIVE-GRANTORS": ("Total P2P Active Grantors", "raw"),
    "NUM-ACTIVE-P2P-AGE-GT-36M": ("Num Active P2P Age GT 36M", "raw"),
    "WORST-P2P-DELINQ-IN-LAST-36-MONTHS": ("Worst P2P Delinq In Last 36 Months", "raw"),
    "TOTAL-P2P-MONTHLY-EMI-AMOUNT": ("Total P2P Monthly EMI Amount", "amount"),
    "TOTAL-P2P-BL-ACTIVE": ("Total P2P BL Active", "raw"),
    "MAX-SANCTION-AMOUNT-ALL-ACCOUNT": ("Max Sanction Amount All Account", "amount"),
    "TOTAL-SUM-OF-ASSETS-ACTIVE": ("Total Sum Of Assets Active", "amount"),
    "CREDIT-LIMIT-TREND-12-MONTHS": ("Credit Limit Trend 12 Months", "amount"),
    "OVERDUE-AMOUNT-TREND": ("Overdue Amount Trend", "amount"),
    "AVG-PERCENTAGE-INCREASE-HIGH CREDIT": ("Avg Percentage Increase High Credit", "raw"),
    "AVG-PERCENTAGE-INCREASE-CB": ("Avg Percentage Increase CB", "raw"),
    "AVG-PERCENTAGE-INCREASE-DPD": ("Avg Percentage Increase DPD", "raw"),
    "AVG-PERCENTAGE-INCREASE-AO": ("Avg Percentage Increase AO", "raw"),
}

SUMMARY_COLUMNS: tuple[tuple[str, str, str], ...] = (
    # (header, field, kind)
    ("Number of Accounts", "number_of_accounts", "count"),
    ("Active Accounts", "active_accounts", "count"),
    ("Overdue Accounts", "overdue_accounts", "count"),
    ("Secured Accounts", "secured_accounts", "count"),
    ("UnSecured Accounts", "unsecured_accounts", "count"),
    ("Untagged Accounts", "untagged_accounts", "count"),
    ("Total Current Balance", "total_current_balance", "amount"),
    ("Total Sanctioned Amount", "total_sanctioned_amt", "amount"),
    ("Total Disbursed Amount", "total_disbursed_amt", "amount"),
    ("Total Amount Overdue", "total_amt_overdue", "amount"),
)

MFI_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Number Of Accounts:", "number_of_accounts", "count"),
    ("Active Accounts:", "active_accounts", "count"),
    ("Overdue Accounts:", "overdue_accounts", "count"),
    ("Closed Accounts:", "closed_accounts", "count"),
    ("No Of Other Mfis:", "no_of_other_mfis", "count"),
    ("No Of Own Mfis:", "no_of_own_mfis", "count"),
    ("Total Own Current Balance:", "total_own_current_balance", "amount"),
    ("Total Own Installment Amt:", "total_own_installment_amt", "amount"),
    ("Total Own Disbursed Amt:", "total_own_disbursed_amt", "amount"),
    ("Total Own Overdue Amt:", "total_own_overdue_amt", "amount"),
    ("Total Other Current Balance:", "total_other_current_balance", "amount"),
    ("Total Other Installment Amt:", "total_other_installment_amt", "amount"),
    ("Total Other Disbursed Amt:", "total_other_disbursed_amt", "amount"),
    ("Total Other Overdue Amt:", "total_other_overdue_amt", "amount"),
    ("Max Worst Delinquency:", "max_worst_delinquency", "raw"),
)

#: Variation group key -> (sub-heading, first column header). Order = render order.
VARIATION_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("NAME", "Name Variations", "Name"),
    ("EMAIL", "Email-ID Variations", "Email"),
    ("DOB", "DOB Variations", "DOB"),
    ("PHONE", "Phone Variations", "Phone"),
    ("ID", "ID Variations", "ID"),
)
_ID_VARIATION_PREFIXES = ("PAN", "VOTER", "PASSPORT", "UID", "AADHAAR", "AADHAR",
                          "DRIVING", "RATION", "ID")

#: Tradeline HISTORY name -> (sub-heading, value kind). Order = render order.
HISTORY_GRIDS: tuple[tuple[str, str, str], ...] = (
    ("COMBINED-PAYMENT-HISTORY", "Payment History/Asset Classification:", "raw"),
    ("HIGH-CREDIT-HISTORY", "High Credit / Sanctioned Amount History:", "amount"),
    ("CURRENT-BALANCE-HISTORY", "Current Balance History:", "amount"),
    ("AMT-PAID-HISTORY", "Amount Paid History:", "amount"),
)

MONTH_HEADERS = list(fmt.MONTH_ABBR)
MAX_SCORE_FACTORS = 4


@dataclass(frozen=True)
class RenderOptions:
    """Per-call rendering options (no global state)."""

    empty: str = "-"
    mask_account_numbers: bool = False
    #: Sequence of ATTR-NAMEs, or the string ``"all"`` for every attribute present.
    perform_attributes: Sequence[str] | str = field(default=DEFAULT_PERFORM_ATTRIBUTES)
    #: Override the footer timestamp (defaults to "now" in IST).
    generated_at: datetime | None = None
    #: Applicant gender supplied by the caller. Wins over the JSON's
    #: ``APPLICANT-SEGMENT.GENDER``; ``None`` / blank falls back to the JSON.
    gender: str | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_FORMATTERS = {
    "raw": fmt.clean,
    "amount": fmt.format_amount,
    "count": fmt.format_count,
    "date": fmt.format_date,
    "percent": fmt.format_percent,
    "installment": fmt.format_installment,
}


class _Ctx:
    def __init__(self, options: RenderOptions):
        self.options = options

    def show(self, value: Any, kind: str = "raw") -> str:
        """Format and substitute the empty placeholder."""
        return fmt.or_placeholder(_FORMATTERS[kind](value), self.options.empty)

    def account_no(self, value: Any) -> str | None:
        if self.options.mask_account_numbers:
            return fmt.mask_value(value)
        return fmt.clean(value)


def _pairs_to_rows(pairs: Iterable[tuple[str, str]], per_row: int) -> list[list[dict]]:
    """Chunk (label, value) pairs into grid rows, padding the last row."""
    items = [{"label": label, "value": value} for label, value in pairs]
    rows = [items[i:i + per_row] for i in range(0, len(items), per_row)]
    if rows:
        rows[-1] += [{"label": "", "value": ""}] * (per_row - len(rows[-1]))
    return rows


def _split_pipe(text: str) -> list[str]:
    """Split a pipe series; drop the single trailing empty element CRIF appends."""
    if not text:
        return []
    parts = text.split("|")
    if text.endswith("|"):
        parts = parts[:-1]
    return parts


def full_name(report: B2CReport) -> str:
    app = report.request_data.applicant_segment
    parts = (fmt.clean(app.first_name), fmt.clean(app.middle_name), fmt.clean(app.last_name))
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def _header(report: B2CReport, c: _Ctx) -> list[list[dict]]:
    h = report.header_segment
    return _pairs_to_rows([
        ("Report ID:", c.show(h.report_id)),
        ("Status:", c.show(h.status)),
        ("Date of Issue:", c.show(h.date_of_issue, "date")),
        ("Date of Request:", c.show(h.date_of_request, "date")),
        ("Product Type:", c.show(h.product_type)),
        ("Product Version:", c.show(h.product_ver)),
    ], 3)


def _address_text(addr) -> str | None:
    text = (fmt.clean(addr.addresstext) or "").rstrip(", ")
    upper = text.upper()
    extras = []
    for part in (addr.city, addr.state, addr.pin):
        part = fmt.clean(part)
        if part and part.upper() not in upper:
            extras.append(part)
            upper += " " + part.upper()
    return ", ".join(p for p in [text] + extras if p) or None


def resolve_gender(report: B2CReport, options: RenderOptions) -> str | None:
    """Caller-supplied gender if non-blank, else ``APPLICANT-SEGMENT.GENDER``; never guessed."""
    return (fmt.gender_label(options.gender)
            or fmt.gender_label(report.request_data.applicant_segment.gender))


def _inquiry_input(report: B2CReport, c: _Ctx) -> dict:
    app = report.request_data.applicant_segment
    pairs: list[tuple[str, str]] = [
        ("Name:", c.show(full_name(report))),
        ("Gender:", resolve_gender(report, c.options) or ""),  # unknown -> blank, never "-"
    ]
    dob = fmt.format_date(app.dob.dob_dt)
    if dob:
        pairs.append(("Date of Birth:", dob))
    phones = [p for p in (fmt.clean(x.value) for x in app.phones) if p]
    pairs.append(("Phone Numbers:", c.show(", ".join(phones))))
    for id_ in app.ids:
        value = fmt.clean(id_.value)
        if value:
            pairs.append((f"{fmt.id_type_label(id_.type) or 'ID'}:", value))
    emails = [e for e in (fmt.clean(x.email) for x in app.emails) if e]
    if emails:
        pairs.append(("Email:", ", ".join(emails)))

    addresses = [a for a in (_address_text(a) for a in app.addresses) if a]
    full_rows = [
        {"label": "Address:" if len(addresses) == 1 else f"Address {i}:", "value": a}
        for i, a in enumerate(addresses, start=1)
    ]
    return {"rows": _pairs_to_rows(pairs, 2), "full_rows": full_rows}


def _scores(report: B2CReport, c: _Ctx) -> list[dict]:
    out = []
    for s in report.report_data.standard_data.score:
        factors = [f for f in (fmt.clean(x.desc) for x in s.factors) if f][:MAX_SCORE_FACTORS]
        out.append({
            "name": c.show(s.name),
            "range": "",  # not provided by CRIF JSON (blank, as in the reference)
            "value": c.show(s.value),
            "grade": c.show(s.description),
            "factors": factors or [c.options.empty],
        })
    return out


def _trend(report: B2CReport, c: _Ctx) -> dict | None:
    t = report.report_data.trends
    dates = _split_pipe(t.dates)
    values = _split_pipe(t.values)
    if not any(fmt.clean(d) for d in dates):
        return None
    labels = [fmt.quarter_label(d) or "" for d in dates]
    scores = [c.show(values[i] if i < len(values) else "") for i in range(len(dates))]
    return {"labels": labels, "scores": scores}


def _summary(block, c: _Ctx) -> list[str]:
    return [c.show(getattr(block, name), kind) for _, name, kind in SUMMARY_COLUMNS]


def _mfi(report: B2CReport, c: _Ctx) -> list[list[dict]]:
    m = report.report_data.accounts_summary.mfi_group_accounts_summary
    return _pairs_to_rows(
        [(label, c.show(getattr(m, name), kind)) for label, name, kind in MFI_FIELDS], 2
    )


def _additional(report: B2CReport, c: _Ctx) -> list[list[dict]]:
    pairs = [
        (f"{fmt.title_label(a.attr_name)}:", c.show(a.attr_value))
        for a in report.report_data.accounts_summary.additional_summary
        if fmt.clean(a.attr_name)
    ]
    return _pairs_to_rows(pairs, 2)


def _perform(report: B2CReport, c: _Ctx) -> list[list[dict]]:
    present: dict[str, str] = {}
    for a in report.report_data.accounts_summary.perform_attributes:
        name = fmt.clean(a.attr_name)
        if name:
            present.setdefault(name.upper(), a.attr_value)

    wanted = c.options.perform_attributes
    names = list(present) if wanted == "all" else [n.strip().upper() for n in wanted]

    pairs = []
    for name in names:
        if name not in present:
            continue
        label, kind = PERFORM_ATTRIBUTE_CATALOGUE.get(name, (fmt.title_label(name), "raw"))
        pairs.append((f"{label}:", c.show(present[name], kind)))
    return _pairs_to_rows(pairs, 2)


def _variation_group_key(var_type: str) -> str:
    key = (fmt.clean(var_type) or "").upper()
    key = key.replace("-VARIATIONS", "").replace("_VARIATIONS", "")
    return "ID" if key.startswith(_ID_VARIATION_PREFIXES) else key


def _variation_rows(variations, c: _Ctx) -> list[list[str]]:
    return [[
        c.show(v.value),
        c.show(v.first_reported_dt, "date"),
        c.show(v.reported_dt, "date"),
        c.show(fmt.join_csv(v.loan_type_assoc)),
        c.show(fmt.join_csv(v.source_indicator)),
    ] for v in variations]


def _variations(report: B2CReport, c: _Ctx) -> dict:
    grouped: dict[str, list] = {}
    for group in report.report_data.standard_data.demogs.variations:
        values = [v for v in group.variation if fmt.clean(v.value)]  # a variation without a value says nothing
        if values:
            grouped.setdefault(_variation_group_key(group.type) or "OTHER", []).extend(values)

    address = grouped.pop("ADDRESS", [])
    tables = []
    if grouped.get("EMAIL"):  # allow a line break after "@" in the narrow first column
        grouped["EMAIL"] = [v.model_copy(update={"value": (fmt.clean(v.value) or "").replace("@", "@​")})
                            for v in grouped["EMAIL"]]
    for key, title, first_col in VARIATION_GROUPS:
        if grouped.get(key):
            tables.append({"title": title, "first_col": first_col,
                           "rows": _variation_rows(grouped.pop(key), c)})
    for key, items in grouped.items():  # unknown variation types, rendered generically
        tables.append({"title": f"{fmt.title_label(key)} Variations", "first_col": "Value",
                       "rows": _variation_rows(items, c)})
    return {"tables": tables, "address_rows": _variation_rows(address, c)}


def _employment(report: B2CReport, c: _Ctx) -> list[list[str]]:
    rows = []
    for wrapper in report.report_data.standard_data.employment_details:
        e = wrapper.employment_detail
        if all(fmt.is_empty(x) for x in (e.occupation, e.first_reported_dt, e.last_reported_dt,
                                          e.acct_type, e.source_indicator)):
            continue
        rows.append([
            c.show(e.occupation),
            c.show(e.first_reported_dt, "date"),
            c.show(e.last_reported_dt, "date"),
            c.show(e.acct_type),
            c.show(e.source_indicator),
        ])
    return rows


def _history_grid(history: History, kind: str) -> list[dict] | None:
    """Month-wise grid: one row per year (ascending), Jan..Dec cells. None if all empty."""
    dates = _split_pipe(history.dates)
    values = _split_pipe(history.values)
    cells: dict[int, list[str]] = {}
    has_value = False
    for i, raw_date in enumerate(dates):
        key = fmt.parse_month_key(raw_date)
        if key is None:
            continue
        year, month = key
        row = cells.setdefault(year, [""] * 12)
        value = _FORMATTERS[kind](values[i] if i < len(values) else "")
        if value:
            has_value = True
            row[month - 1] = value
    if not has_value:
        return None
    return [{"year": str(year), "cells": cells[year]} for year in sorted(cells)]


def _account(t: Tradeline, c: _Ctx) -> dict:
    acct_no = c.account_no(t.acct_number)
    strip = [
        ("Account Type:", c.show(t.acct_type)),
        ("Credit Grantor:", c.show(t.credit_grantor)),
        ("Account #:", c.show(acct_no)),
        ("Lender Type #:", c.show(fmt.lender_type_label(t.credit_grantor_type))),
        ("As on #:", c.show(t.reported_dt, "date")),
    ]
    grid = _pairs_to_rows([
        ("Ownership:", c.show(t.ownership_type)),
        ("Security Status:", c.show(t.security_status)),
        ("Disbursed Date:", c.show(t.disbursed_dt, "date")),
        ("Disbd Amt/High Credit:", c.show(t.disbursed_amt, "amount")),
        ("Credit Limit:", c.show(t.credit_limit, "amount")),
        ("Interest Rate (%):", c.show(t.interest_rate, "percent")),
        ("Last Payment Date:", c.show(t.last_payment_dt, "date")),
        ("Current Balance:", c.show(t.current_bal, "amount")),
        ("Cash Limit:", c.show(t.cash_limit, "amount")),
        ("Closed Date:", c.show(t.closed_dt, "date")),
        ("Last Paid Amt:", c.show(t.last_paid_amount, "amount")),
        ("InstlAmt/Freq:", c.show(t.installment_amt, "installment")),
        ("Tenure(month):", c.show(t.repayment_tenure, "count")),
        ("Overdue Amt:", c.show(t.overdue_amt, "amount")),
        ("Write off Date:", c.show(t.write_off_dt, "date")),
        ("Account in Dispute:", c.show(t.acct_in_dispute)),
        ("Account Remarks:", c.show(t.account_remarks)),
        ("Principal Writeoff Amt:", c.show(t.principal_write_off_amt, "amount")),
        ("Total Writeoff Amt:", c.show(t.write_off_amt, "amount")),
        ("Settlement Amt:", c.show(t.settlement_amt, "amount")),
    ], 3)

    caption = " | ".join(
        p for p in (acct_no, fmt.clean(t.acct_type), fmt.clean(t.credit_grantor)) if p
    )
    by_name = {(fmt.clean(h.name) or "").upper(): h for h in t.history}
    histories = []
    for name, title, kind in HISTORY_GRIDS:
        rows = _history_grid(by_name[name], kind) if name in by_name else None
        if rows:
            histories.append({"title": title, "caption": caption, "rows": rows})

    return {
        "strip": [{"label": label, "value": value} for label, value in strip],
        "status": c.show(t.account_status),
        "grid": grid,
        "histories": histories,
    }


def _inquiries(report: B2CReport, c: _Ctx) -> list[list[str]]:
    return [[
        c.show(fmt.clean(q.member_name) or q.lender_name),
        c.show(q.inquiry_date, "date"),
        c.show(q.purpose),
        c.show(q.ownership_type),
        c.show(q.amount, "amount"),
        c.show(q.remark),
    ] for q in report.report_data.standard_data.inquiry_history]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def build_view_model(report: B2CReport, options: RenderOptions | None = None) -> dict:
    options = options or RenderOptions()
    c = _Ctx(options)
    name = full_name(report)
    acc_summary = report.report_data.accounts_summary
    return {
        "title": f"Credit Information Report - {name}" if name else "Credit Information Report",
        "name": name,  # "" -> the "For <name>" line is omitted
        "report_id": fmt.clean(report.header_segment.report_id) or "",
        "generated_at": fmt.format_generated_at(options.generated_at),
        "empty": options.empty,
        "header_rows": _header(report, c),
        "inquiry": _inquiry_input(report, c),
        "scores": _scores(report, c),
        "trend": _trend(report, c),
        "summary_headers": [h for h, _, _ in SUMMARY_COLUMNS],
        "primary_summary": _summary(acc_summary.primary_accounts_summary, c),
        "secondary_summary": _summary(acc_summary.secondary_accounts_summary, c),
        "mfi_rows": _mfi(report, c),
        "additional_rows": _additional(report, c),
        "perform_rows": _perform(report, c),
        "variations": _variations(report, c),
        "employment_rows": _employment(report, c),
        "accounts": [_account(t, c) for t in report.report_data.standard_data.tradelines],
        "inquiry_rows": _inquiries(report, c),
        "month_headers": MONTH_HEADERS,
    }
