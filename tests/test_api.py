"""Input handling, validation errors and the view-model (no PDF rendering: fast)."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from crif_pdf_engine_digitap import (
    CrifReportError,
    build_context,
    render_html,
    suggested_filename,
)
from crif_pdf_engine_digitap.mapper import DEFAULT_PERFORM_ATTRIBUTES

from .conftest import GENERATED_AT, SAMPLE, fixture_path


# --------------------------------------------------------------- input forms
def test_accepts_dict_json_string_bytes_and_paths(sample_dict):
    expected = build_context(sample_dict, generated_at=GENERATED_AT)
    text = SAMPLE.read_text(encoding="utf-8")
    for data in (text, text.encode("utf-8"), SAMPLE, str(SAMPLE)):
        assert build_context(data, generated_at=GENERATED_AT) == expected


def test_accepts_unwrapped_b2c_report(sample_dict):
    b2c = sample_dict["data"]["report_json"]["parsed_data"]["B2C-REPORT"]
    assert build_context(b2c)["report_id"] == "CCR261006CR581766645"
    assert build_context({"B2C-REPORT": b2c})["report_id"] == "CCR261006CR581766645"


def test_accepts_double_encoded_report_json(sample_dict):
    doc = dict(sample_dict)
    doc["data"] = {"report_json": json.dumps(sample_dict["data"]["report_json"])}
    assert build_context(doc)["report_id"] == "CCR261006CR581766645"


# -------------------------------------------------------------------- errors
@pytest.mark.parametrize("name, message", [
    ("failed_envelope", "No record found"),
    ("failed_header_status", "FAILED"),
    ("empty_report", "empty"),
])
def test_failed_reports_raise_clear_error(name, message):
    with pytest.raises(CrifReportError, match=message):
        render_html(fixture_path(name))


@pytest.mark.parametrize("data, message", [
    ("{not json", "Invalid JSON"),
    ("does/not/exist.json", "neither JSON nor a path"),
    ("[1, 2]", "must be an object"),
    ({"foo": "bar"}, "Could not find"),
    (12345, "Unsupported input type"),
])
def test_invalid_input_raises(data, message):
    with pytest.raises(CrifReportError, match=message):
        render_html(data)


def test_error_is_a_value_error():
    assert issubclass(CrifReportError, ValueError)


# ---------------------------------------------------------------- view-model
@pytest.fixture(scope="module")
def ctx(sample_dict):
    return build_context(sample_dict, generated_at=GENERATED_AT)


def test_header_and_name(ctx):
    assert ctx["name"] == "ANAND VARDHAN GOYAL"
    assert ctx["title"] == "Credit Information Report - ANAND VARDHAN GOYAL"
    assert ctx["generated_at"] == "06-10-2026 17:02"
    values = {i["label"]: i["value"] for row in ctx["header_rows"] for i in row}
    assert values["Report ID:"] == "CCR261006CR581766645"
    assert values["Status:"] == "SUCCESS"


def test_inquiry_input_shows_optional_rows(ctx):
    values = {i["label"]: i["value"] for row in ctx["inquiry"]["rows"] for i in row}
    assert values["Date of Birth:"] == "04-10-1995"
    assert values["PAN:"] == "CAZPG3241C"
    assert values["Email:"] == "anandvardhan001@gmail.com"
    assert ctx["inquiry"]["full_rows"][0]["value"].endswith("PB, 148035")


def test_score_and_real_trend(ctx):
    assert ctx["scores"][0]["value"] == "800"
    assert ctx["scores"][0]["grade"] == "A"
    assert ctx["scores"][0]["range"] == ""
    assert ctx["trend"]["labels"][:2] == ["Jun-26", "Mar-26"]
    assert ctx["trend"]["scores"][:3] == ["800", "774", "800"]


def test_summaries_are_indian_formatted(ctx):
    assert ctx["primary_summary"] == ["10", "1", "0", "10", "0", "0", "0", "0", "0", "0"]
    perform = {i["label"]: i["value"] for row in ctx["perform_rows"] for i in row if i["label"]}
    assert len(perform) == len(DEFAULT_PERFORM_ATTRIBUTES) == 9
    assert perform["Total Secured Outstanding:"] == "25,92,764"


def test_perform_attributes_configurable(sample_dict):
    all_ctx = build_context(sample_dict, perform_attributes="all")
    labels = [i["label"] for row in all_ctx["perform_rows"] for i in row if i["label"]]
    assert len(labels) == 92
    one = build_context(sample_dict, perform_attributes=["TOTAL-OBLIGATIONS"])
    assert one["perform_rows"][0][0] == {"label": "Total Obligations:", "value": "25,92,764"}


def test_account_fields(ctx):
    assert len(ctx["accounts"]) == 10
    housing = ctx["accounts"][9]
    strip = {i["label"]: i["value"] for i in housing["strip"]}
    assert strip["Lender Type #:"] == "Nationalised Bank"     # code mapped, never the lender name
    grid = {i["label"]: i["value"] for row in housing["grid"] for i in row}
    assert grid["InstlAmt/Freq:"] == "43,945/Monthly"
    assert grid["Interest Rate (%):"] == "7.85"
    assert grid["Closed Date:"] == "-"                       # empty -> "-"
    assert [h["title"] for h in housing["histories"]] == [
        "Payment History/Asset Classification:", "High Credit / Sanctioned Amount History:",
        "Current Balance History:", "Amount Paid History:",
    ]
    payment = housing["histories"][0]["rows"]
    assert [r["year"] for r in payment] == ["2023", "2024", "2025", "2026"]
    assert payment[-1]["cells"][8] == "000/STD"             # Sep 2026
    # Amount-paid history is all empty for the closed deposit loans -> hidden.
    assert len(ctx["accounts"][0]["histories"]) == 3


def test_variations_grouping(ctx):
    titles = [t["title"] for t in ctx["variations"]["tables"]]
    assert titles == ["Name Variations", "Email-ID Variations", "DOB Variations",
                      "Phone Variations", "ID Variations"]
    assert len(ctx["variations"]["address_rows"]) == 5


def test_masking_option(sample_dict):
    masked = build_context(sample_dict, mask_account_numbers=True)
    strip = {i["label"]: i["value"] for i in masked["accounts"][0]["strip"]}
    assert strip["Account #:"] == "XXXXXXXX2364"


def test_custom_empty_placeholder(sample_dict):
    blank = build_context(sample_dict, empty="")
    grid = {i["label"]: i["value"] for row in blank["accounts"][9]["grid"] for i in row}
    assert grid["Closed Date:"] == ""


def test_html_has_no_unrendered_template_syntax(sample_dict):
    html = render_html(sample_dict)
    assert "{{" not in html and "{%" not in html
    assert "ANAND VARDHAN GOYAL" in html


def test_concurrent_rendering_is_isolated(sample_dict):
    """Different options in parallel threads must not leak into each other."""
    def work(i):
        empty = "-" if i % 2 else "N/A"
        html = render_html(sample_dict, empty=empty, generated_at=GENERATED_AT)
        return empty, html

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(work, range(16)))
    for empty, html in results:
        assert (">N/A<" in html) == (empty == "N/A")


def test_suggested_filename(sample_dict):
    assert suggested_filename(sample_dict) == "CRIF_ANAND_VARDHAN_GOYAL_CCR261006CR581766645.pdf"
