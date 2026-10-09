from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "input" / "sample.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Fixed timestamp so rendered output is deterministic.
GENERATED_AT = datetime(2026, 10, 6, 17, 2)


def fixture_path(name: str) -> Path:
    return FIXTURES / f"{name}.json"


@pytest.fixture(scope="session")
def sample_dict() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def pdf_text(pdf_bytes: bytes) -> tuple[int, str]:
    """(page count, full text) of a PDF."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc).replace("​", "")
    return len(doc), text
