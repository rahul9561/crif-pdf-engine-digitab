"""Pure, stateless formatting helpers.

Every function accepts the messy values CRIF/Digitap send (``""``, ``"  "``,
``None``, ``"null"``, ints, pre-grouped amounts like ``"25,92,764"`` or raw
floats like ``"2592764.0"``) and returns a display string, or ``None`` when the
input is empty. The mapper decides what to show for ``None`` (``"-"`` or blank).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MONTH_INDEX = {m.lower(): i for i, m in enumerate(MONTH_ABBR, start=1)}

_EMPTY_TOKENS = {"", "null", "none", "nan", "n/a"}

# CRIF "lender type" (CREDIT-GRANTOR-TYPE / SOURCE-INDICATOR) codes.
# Unknown codes are displayed raw by `lender_type_label`.
LENDER_TYPE_LABELS: dict[str, str] = {
    "PRB": "Private Bank",
    "NAB": "Nationalised Bank",
    "PSB": "Public Sector Bank",
    "PUB": "Public Sector Bank",
    "FRB": "Foreign Bank",
    "NBF": "NBFC",
    "COP": "Co-operative Bank",
    "RRB": "Regional Rural Bank",
    "SFB": "Small Finance Bank",
    "PAB": "Payments Bank",
    "MFI": "Microfinance Institution",
    "HFC": "Housing Finance Company",
    "ARC": "Asset Reconstruction Company",
    "CCC": "Credit Card Company",
    "OTH": "Others",
}

# CRIF applicant ID type codes (REQUEST-DATA.APPLICANT-SEGMENT.IDS[].TYPE).
ID_TYPE_LABELS: dict[str, str] = {
    "ID01": "Passport",
    "ID02": "Voter ID",
    "ID03": "UID",
    "ID04": "Other ID",
    "ID05": "Ration Card",
    "ID06": "Driving Licence",
    "ID07": "PAN",
}


# --------------------------------------------------------------------------- #
# Basics
# --------------------------------------------------------------------------- #
def clean(value: object) -> str | None:
    """Collapse whitespace; return ``None`` for anything that means "empty"."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in _EMPTY_TOKENS:
        return None
    return text


def is_empty(value: object) -> bool:
    return clean(value) is None


def or_placeholder(value: str | None, placeholder: str = "-") -> str:
    return placeholder if value is None else value


def join_csv(value: object, sep: str = ", ") -> str | None:
    """``"A,B ,C"`` -> ``"A, B, C"`` (CRIF packs multiple values with commas)."""
    text = clean(value)
    if text is None:
        return None
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return sep.join(parts) or None


def title_label(attr_name: object) -> str:
    """``"NUM-GRANTORS-DELINQ"`` -> ``"Num Grantors Delinq"``."""
    text = clean(attr_name) or ""
    words = re.split(r"[-_\s]+", text)
    return " ".join(w.capitalize() for w in words if w)


# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #
def parse_decimal(value: object) -> Decimal | None:
    """Parse ``"25,92,764"``, ``"2592764.0"``, ``"₹ 1,000"``, ``12`` ...; else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = clean(value)
    if text is None:
        return None
    text = text.replace(",", "").replace("₹", "").replace("Rs.", "").replace(" ", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def indian_group(number: int) -> str:
    """``2592764`` -> ``"25,92,764"`` (lakh/crore grouping)."""
    sign = "-" if number < 0 else ""
    digits = str(abs(number))
    if len(digits) <= 3:
        return sign + digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups) + "," + tail


def format_amount(value: object) -> str | None:
    """Indian-grouped whole rupees. Non-numeric text is passed through unchanged."""
    number = parse_decimal(value)
    if number is None:
        return clean(value)
    return indian_group(int(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def format_count(value: object) -> str | None:
    """``"0.0"`` -> ``"0"``, ``"10"`` -> ``"10"``."""
    number = parse_decimal(value)
    if number is None:
        return clean(value)
    return str(int(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def format_percent(value: object, places: int = 2) -> str | None:
    """``"0.0"`` -> ``"0.00"``, ``"7.85"`` -> ``"7.85"``."""
    number = parse_decimal(value)
    if number is None:
        return clean(value)
    return f"{number:.{places}f}"


def format_installment(value: object) -> str | None:
    """``"31,314/Monthly"`` -> ``"31,314/Monthly"``; ``"16000/null"`` -> ``"16,000"``."""
    text = clean(value)
    if text is None:
        return None
    amount, _, freq = text.partition("/")
    amount_text = format_amount(amount)
    freq_text = clean(freq)
    if amount_text is None:
        return freq_text
    return f"{amount_text}/{freq_text}" if freq_text else amount_text


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #
_DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d%m%Y", "%Y-%m-%dT%H:%M:%S")


def parse_date(value: object) -> date | None:
    text = clean(value)
    if text is None:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_date(value: object) -> str | None:
    """Any supported date -> ``DD-MM-YYYY``. Unparseable text is passed through."""
    parsed = parse_date(value)
    if parsed is None:
        return clean(value)
    return parsed.strftime("%d-%m-%Y")


def quarter_label(value: object) -> str | None:
    """Score-trend date ``"30-06-2026"`` -> ``"Jun-26"``."""
    parsed = parse_date(value)
    if parsed is None:
        return clean(value)
    return f"{MONTH_ABBR[parsed.month - 1]}-{parsed.year % 100:02d}"


def parse_month_key(value: object) -> tuple[int, int] | None:
    """History key ``"Jul:2026"`` -> ``(2026, 7)``."""
    text = clean(value)
    if text is None:
        return None
    match = re.fullmatch(r"([A-Za-z]{3})[A-Za-z]*[:\-/ ](\d{4})", text)
    if not match:
        return None
    month = _MONTH_INDEX.get(match.group(1).lower())
    return (int(match.group(2)), month) if month else None


def format_generated_at(moment: datetime | None = None) -> str:
    """Render timestamp in IST: ``DD-MM-YYYY HH:MM``."""
    moment = moment or datetime.now(IST)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=IST)
    return moment.astimezone(IST).strftime("%d-%m-%Y %H:%M")


# --------------------------------------------------------------------------- #
# Codes & masking
# --------------------------------------------------------------------------- #
def lender_type_label(code: object) -> str | None:
    """Readable lender type; unknown codes are returned raw (never the lender name)."""
    text = clean(code)
    if text is None:
        return None
    return LENDER_TYPE_LABELS.get(text.upper(), text)


def id_type_label(code: object) -> str | None:
    text = clean(code)
    if text is None:
        return None
    return ID_TYPE_LABELS.get(text.upper(), text)


def mask_value(value: object, visible: int = 4, mask_char: str = "X") -> str | None:
    """``"356305002364"`` -> ``"XXXXXXXX2364"``. Already-masked values are untouched."""
    text = clean(value)
    if text is None or len(text) <= visible:
        return text
    return mask_char * (len(text) - visible) + text[-visible:]
