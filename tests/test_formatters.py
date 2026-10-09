from datetime import datetime, timezone

import pytest

from crif_pdf_engine import formatters as f


@pytest.mark.parametrize("value, expected", [
    (0, "0"), (999, "999"), (1000, "1,000"), (100000, "1,00,000"),
    (2592764, "25,92,764"), (81981000, "8,19,81,000"), (-123456, "-1,23,456"),
])
def test_indian_group(value, expected):
    assert f.indian_group(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("2592764.0", "25,92,764"), ("25,92,764", "25,92,764"), ("0.0", "0"), ("0", "0"),
    (125283, "1,25,283"), ("1,11,600", "1,11,600"), ("₹ 1,000.50", "1,001"),
    ("", None), ("  ", None), (None, None), ("null", None), ("XXX", "XXX"),
])
def test_format_amount(value, expected):
    assert f.format_amount(value) == expected


def test_counts_and_percent():
    assert f.format_count("0.0") == "0"
    assert f.format_count("10") == "10"
    assert f.format_percent("0.0") == "0.00"
    assert f.format_percent("7.85") == "7.85"
    assert f.format_percent("") is None


@pytest.mark.parametrize("value, expected", [
    ("31,314/Monthly", "31,314/Monthly"), ("16000/null", "16,000"), ("43945/", "43,945"),
    ("", None), ("/Monthly", "Monthly"),
])
def test_format_installment(value, expected):
    assert f.format_installment(value) == expected


def test_dates():
    assert f.format_date("06-10-2026") == "06-10-2026"
    assert f.format_date("2026-10-06") == "06-10-2026"
    assert f.format_date("") is None
    assert f.format_date("not a date") == "not a date"
    assert f.quarter_label("30-06-2026") == "Jun-26"
    assert f.quarter_label("31-12-2023") == "Dec-23"
    assert f.parse_month_key("Jul:2026") == (2026, 7)
    assert f.parse_month_key("garbage") is None


def test_generated_at_is_ist():
    utc = datetime(2026, 10, 6, 11, 32, tzinfo=timezone.utc)
    assert f.format_generated_at(utc) == "06-10-2026 17:02"


def test_codes_and_masking():
    assert f.lender_type_label("PRB") == "Private Bank"
    assert f.lender_type_label("nab") == "Nationalised Bank"
    assert f.lender_type_label("ZZZ") == "ZZZ"          # unknown -> raw code
    assert f.lender_type_label("") is None
    assert f.id_type_label("ID07") == "PAN"
    assert f.mask_value("356305002364") == "XXXXXXXX2364"
    assert f.mask_value("123") == "123"


def test_text_helpers():
    assert f.clean("  A   B ") == "A B"
    assert f.clean("NULL") is None
    assert f.join_csv("PRB,PRB ,NAB") == "PRB, PRB, NAB"
    assert f.title_label(" NUM-GRANTORS-DELINQ") == "Num Grantors Delinq"
