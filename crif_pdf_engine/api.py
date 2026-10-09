"""Public API: ``render_pdf`` / ``render_html``.

Thread-safety: no mutable module state. The Jinja environment is created once
and only read afterwards (Jinja documents this as safe to share); each call
builds its own WeasyPrint ``HTML`` and ``FontConfiguration``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Union

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import ValidationError

from .mapper import RenderOptions, build_view_model
from .models import B2CReport

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

ReportInput = Union[Mapping[str, Any], str, bytes, os.PathLike]

_SUCCESS_RESULT_CODES = {101}
_SUCCESS_STATUSES = {"SUCCESS"}


class CrifReportError(ValueError):
    """Input is not a usable CRIF report (bad JSON, failed/empty status, ...)."""


# --------------------------------------------------------------------------- #
# Input handling
# --------------------------------------------------------------------------- #
def _load(data: ReportInput) -> Any:
    if isinstance(data, Mapping):
        return data
    if isinstance(data, os.PathLike):
        return _read_file(Path(data))
    if isinstance(data, bytes):
        data = data.decode("utf-8-sig")
    if isinstance(data, str):
        text = data.strip()
        if text.startswith(("{", "[")):
            return _parse_json(text, "input string")
        path = Path(text)
        if path.is_file():
            return _read_file(path)
        raise CrifReportError(
            "Input string is neither JSON nor a path to an existing file: "
            f"{text[:80]!r}"
        )
    raise CrifReportError(f"Unsupported input type: {type(data).__name__}")


def _read_file(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CrifReportError(f"Cannot read input file {path}: {exc}") from exc
    return _parse_json(text, str(path))


def _parse_json(text: str, source: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CrifReportError(f"Invalid JSON in {source}: {exc}") from exc


def _maybe_json(value: Any) -> Any:
    """Some integrations double-encode nested blocks as JSON strings."""
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _extract_b2c(raw: Any) -> Mapping[str, Any]:
    """Accept the full Digitap envelope, ``parsed_data``, ``B2C-REPORT`` or its body."""
    if not isinstance(raw, Mapping):
        raise CrifReportError("CRIF report JSON must be an object at the top level.")

    if raw.get("success") is False:
        raise CrifReportError(
            f"Report request failed: {raw.get('message') or 'success=false'} "
            f"(result_code={raw.get('result_code')})"
        )
    code = raw.get("result_code")
    if code is not None and "data" in raw and code not in _SUCCESS_RESULT_CODES:
        raise CrifReportError(
            f"Report request failed: {raw.get('message') or 'unknown error'} "
            f"(result_code={code})"
        )

    node: Any = raw
    for key in ("data", "report_json", "parsed_data"):
        if isinstance(node, Mapping) and key in node:
            node = _maybe_json(node[key])
    if isinstance(node, Mapping) and "B2C-REPORT" in node:
        node = _maybe_json(node["B2C-REPORT"])

    if isinstance(node, Mapping) and not node:
        raise CrifReportError("CRIF report is empty (B2C-REPORT has no content).")
    if not isinstance(node, Mapping) or not (
        "HEADER-SEGMENT" in node or "REPORT-DATA" in node
    ):
        raise CrifReportError(
            "Could not find a CRIF 'B2C-REPORT' (expected HEADER-SEGMENT / REPORT-DATA) "
            "in the input."
        )
    return node


def parse_report(data: ReportInput) -> B2CReport:
    """Load, locate and validate a CRIF report; raises ``CrifReportError``."""
    body = _extract_b2c(_load(data))
    try:
        report = B2CReport.model_validate(body)
    except ValidationError as exc:  # pragma: no cover - models are very tolerant
        raise CrifReportError(f"CRIF report has an unexpected structure: {exc}") from exc

    status = (report.header_segment.status or "").strip().upper()
    if status and status not in _SUCCESS_STATUSES:
        raise CrifReportError(f"CRIF report status is {status!r}, expected 'SUCCESS'.")
    if not status and not report.report_data.standard_data.tradelines \
            and not report.header_segment.report_id.strip():
        raise CrifReportError("CRIF report is empty (no status, report ID or accounts).")
    return report


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _options(options: RenderOptions | None, overrides: dict) -> RenderOptions:
    if options is None:
        return RenderOptions(**overrides)
    if overrides:
        from dataclasses import replace
        return replace(options, **overrides)
    return options


def build_context(data: ReportInput, options: RenderOptions | None = None,
                  **overrides: Any) -> dict:
    """The template view-model (useful for debugging / custom templates)."""
    return build_view_model(parse_report(data), _options(options, overrides))


def render_html(data: ReportInput, options: RenderOptions | None = None,
                **overrides: Any) -> str:
    """Render the report as an HTML string (asset URLs are relative to ``STATIC_DIR``)."""
    context = build_context(data, options, **overrides)
    return _jinja_env().get_template("base.html").render(r=context)


def render_pdf(data: ReportInput, output_path: str | os.PathLike | None = None,
               options: RenderOptions | None = None, **overrides: Any) -> bytes:
    """Render the report to PDF bytes; also write them to ``output_path`` if given.

    ``data`` may be a dict, a JSON string, bytes, or a path (str / Path) to a JSON file.
    Keyword overrides map to :class:`RenderOptions` fields, e.g.
    ``render_pdf(data, empty="", mask_account_numbers=True, perform_attributes="all")``.
    """
    from weasyprint import HTML  # imported lazily: heavy, and needs native libs
    from weasyprint.text.fonts import FontConfiguration

    html = render_html(data, options, **overrides)
    font_config = FontConfiguration()
    pdf_bytes = HTML(string=html, base_url=str(STATIC_DIR)).write_pdf(
        font_config=font_config
    )
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
    return pdf_bytes


def suggested_filename(data: ReportInput) -> str:
    """``"CRIF_ANAND_VARDHAN_GOYAL_CCR261006CR581766645.pdf"`` (safe for headers)."""
    import re

    from .mapper import full_name

    report = parse_report(data)
    parts = ["CRIF", full_name(report), report.header_segment.report_id.strip()]
    stem = "_".join(p for p in parts if p)
    return re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") + ".pdf"
