"""End-to-end PDF rendering (WeasyPrint). Each document is rendered once per module."""

import pytest

from crif_pdf_engine_digitap import render_pdf
from crif_pdf_engine_digitap.cli import main as cli_main

from .conftest import GENERATED_AT, SAMPLE, fixture_path, pdf_text


@pytest.fixture(scope="module")
def sample_pdf():
    return render_pdf(SAMPLE, generated_at=GENERATED_AT)


def test_sample_renders_non_empty_pdf(sample_pdf):
    assert sample_pdf.startswith(b"%PDF")
    assert len(sample_pdf) > 20_000


def test_sample_page_count_is_reasonable(sample_pdf):
    pages, _ = pdf_text(sample_pdf)
    assert 8 <= pages <= 20


def test_sample_key_values_in_text(sample_pdf):
    pages, text = pdf_text(sample_pdf)
    # The report ID wraps inside its narrow column (as in the reference PDF).
    assert "CCR261006CR581766645" in text.replace("\n", "")
    for expected in (
        "ANAND VARDHAN GOYAL", "PERFORM CONSUMER 2.2",
        "800", "25,92,764", "Nationalised Bank", "43,945/Monthly", "-END OF REPORT-",
        "Generated: 06-10-2026 17:02", f"Page 1 of {pages}", f"Page {pages} of {pages}",
    ):
        assert expected in text, expected
    assert "/null" not in text


def test_fonts_are_embedded_from_package(sample_pdf):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open(stream=sample_pdf, filetype="pdf")
    fonts = {f[3].split("+")[-1] for page in doc for f in page.get_fonts()}
    assert any(f.startswith("Roboto") for f in fonts)
    assert any(f.startswith("Montserrat") for f in fonts)
    assert not any("Helvetica" in f or "DejaVu" in f for f in fonts)


def test_output_path_writes_file(tmp_path):
    out = tmp_path / "nested" / "report.pdf"
    data = render_pdf(fixture_path("no_accounts"), output_path=out)
    assert out.read_bytes() == data


def test_no_accounts(tmp_path):
    pages, text = pdf_text(render_pdf(fixture_path("no_accounts")))
    assert pages <= 4
    assert "No records found" in text
    assert "Employment Details" not in text


def test_null_fields_everywhere():
    pages, text = pdf_text(render_pdf(fixture_path("null_fields")))
    assert pages >= 1
    assert "CCR000000NULLTEST" in text.replace("\n", "")
    assert "For -" not in text


@pytest.mark.slow
def test_hundred_accounts():
    pages, text = pdf_text(render_pdf(fixture_path("many_accounts_100")))
    assert 50 <= pages <= 150
    assert text.count("Account Status:") == 100
    assert "TEST000000000099" in text
    assert "Inquiry History" in text
    assert "ZZZ" in text                                  # unknown lender code shown raw


def test_cli_writes_pdf(tmp_path, capsys):
    out = tmp_path / "cli.pdf"
    assert cli_main([str(fixture_path("no_accounts")), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")


def test_cli_html_mode(tmp_path):
    out = tmp_path / "cli.html"
    assert cli_main([str(SAMPLE), "--html", "-o", str(out)]) == 0
    assert "Credit Information" in out.read_text(encoding="utf-8")


def test_cli_reports_error(capsys):
    assert cli_main([str(fixture_path("failed_envelope"))]) == 2
    assert "No record found" in capsys.readouterr().err
