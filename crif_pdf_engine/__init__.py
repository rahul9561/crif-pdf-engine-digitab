"""CRIF credit-report JSON -> PDF engine (Jinja2 + WeasyPrint)."""

from .api import (
    CrifReportError,
    build_context,
    parse_report,
    render_html,
    render_pdf,
    suggested_filename,
)
from .mapper import DEFAULT_PERFORM_ATTRIBUTES, PERFORM_ATTRIBUTE_CATALOGUE, RenderOptions

__version__ = "0.1.0"

__all__ = [
    "render_pdf",
    "render_html",
    "CrifReportError",
    "RenderOptions",
    "build_context",
    "parse_report",
    "suggested_filename",
    "DEFAULT_PERFORM_ATTRIBUTES",
    "PERFORM_ATTRIBUTE_CATALOGUE",
]
