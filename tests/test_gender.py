"""Gender precedence: caller-supplied gender > APPLICANT-SEGMENT.GENDER > blank."""

import copy

import pytest

from crif_pdf_engine_digitap import RenderOptions, build_context, render_pdf
from crif_pdf_engine_digitap.cli import main as cli_main
from crif_pdf_engine_digitap.formatters import gender_label

from .conftest import pdf_text


def _with_json_gender(sample_dict, gender):
    """Deep copy of the sample with APPLICANT-SEGMENT.GENDER set (or removed if ``...``)."""
    doc = copy.deepcopy(sample_dict)
    app = doc["data"]["report_json"]["parsed_data"]["B2C-REPORT"]["REQUEST-DATA"][
        "APPLICANT-SEGMENT"]
    if gender is ...:
        app.pop("GENDER", None)
    else:
        app["GENDER"] = gender
    return doc


def _ctx_gender(ctx) -> str:
    values = {i["label"]: i["value"] for row in ctx["inquiry"]["rows"] for i in row}
    return values["Gender:"]


def _pdf_gender(pdf_bytes) -> str:
    _, text = pdf_text(pdf_bytes)
    lines = text.splitlines()
    value = lines[lines.index("Gender:") + 1]
    return "" if value.endswith(":") else value  # blank cell -> next line is the next label


# ------------------------------------------------------------- normalisation
@pytest.mark.parametrize("raw, expected", [
    ("Male", "Male"), ("MALE", "Male"), (" male ", "Male"), ("M", "Male"),
    ("Female", "Female"), ("FEMALE", "Female"), ("female", "Female"), ("f", "Female"),
    ("Other", "Other"), ("o", "Other"),
    ("Transgender", "Transgender"),
    ("Something Else", "Something Else"),     # unknown -> shown as sent, never guessed
    ("", None), ("   ", None), (None, None), ("null", None),
])
def test_gender_label(raw, expected):
    assert gender_label(raw) == expected


# ------------------------------------------------------------ view-model
@pytest.mark.parametrize("user, json_gender, expected", [
    ("Female", "Male", "Female"),
    ("Male", "Female", "Male"),
    ("female", "Male", "Female"),
    (None, "Female", "Female"),
    ("", "Male", "Male"),
    ("   ", "Male", "Male"),
    (None, "", ""),
    ("  ", None, ""),
    (None, ..., ""),
    ("Other", "Male", "Other"),
])
def test_gender_precedence_in_context(sample_dict, user, json_gender, expected):
    doc = _with_json_gender(sample_dict, json_gender)
    assert _ctx_gender(build_context(doc, gender=user)) == expected


def test_gender_via_render_options(sample_dict):
    doc = _with_json_gender(sample_dict, "Male")
    assert _ctx_gender(build_context(doc, RenderOptions(gender="Female"))) == "Female"
    # a keyword override still wins over the options object
    assert _ctx_gender(build_context(doc, RenderOptions(gender="Female"), gender="Male")) == "Male"


def test_missing_gender_is_blank_not_placeholder(sample_dict):
    doc = _with_json_gender(sample_dict, "")
    assert _ctx_gender(build_context(doc, empty="N/A")) == ""


def test_omitting_gender_argument_uses_json(sample_dict):
    """Existing callers that never pass ``gender`` keep the JSON value."""
    doc = _with_json_gender(sample_dict, "Female")
    assert _ctx_gender(build_context(doc)) == "Female"
    assert _ctx_gender(build_context(doc, RenderOptions())) == "Female"


def test_source_json_is_not_modified(sample_dict):
    doc = _with_json_gender(sample_dict, "Male")
    before = copy.deepcopy(doc)
    build_context(doc, gender="Female")
    assert doc == before


# ------------------------------------------------------------ final PDF
@pytest.mark.parametrize("user, json_gender, expected", [
    ("Female", "Male", "Female"),     # 1. user wins
    ("Male", "Female", "Male"),       # 2. user wins
    (None, "Female", "Female"),       # 3. fallback to JSON
    ("", "Male", "Male"),             # 4. empty user value -> JSON
    ("  ", "Male", "Male"),           # 4. whitespace user value -> JSON
])
def test_gender_in_pdf(sample_dict, user, json_gender, expected):
    doc = _with_json_gender(sample_dict, json_gender)
    assert _pdf_gender(render_pdf(doc, gender=user)) == expected


def test_no_gender_anywhere_in_pdf(sample_dict):
    """5. Neither input nor JSON has a gender -> blank, no invented value."""
    pdf = render_pdf(_with_json_gender(sample_dict, ...))
    assert _pdf_gender(pdf) == ""
    _, text = pdf_text(pdf)
    assert "Male" not in text and "Female" not in text


def test_existing_call_without_gender_in_pdf(sample_dict):
    """6. render_pdf(data) with no gender argument still works and uses the JSON."""
    assert _pdf_gender(render_pdf(_with_json_gender(sample_dict, "Female"))) == "Female"


def test_cli_gender_option(sample_dict, tmp_path):
    import json
    src = tmp_path / "in.json"
    src.write_text(json.dumps(_with_json_gender(sample_dict, "Male")), encoding="utf-8")
    out = tmp_path / "out.pdf"
    assert cli_main([str(src), "--gender", "Female", "-o", str(out)]) == 0
    assert _pdf_gender(out.read_bytes()) == "Female"
