"""Command line: ``crif-pdf input.json -o output.pdf``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .api import CrifReportError, render_html, render_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crif-pdf", description="Render a CRIF credit report JSON to PDF."
    )
    parser.add_argument("input", type=Path, help="CRIF report JSON file")
    parser.add_argument("-o", "--output", type=Path,
                        help="output file (default: <input>.pdf / .html)")
    parser.add_argument("--html", action="store_true",
                        help="write the intermediate HTML instead of a PDF")
    parser.add_argument("--mask-accounts", action="store_true",
                        help="mask account numbers (show last 4 characters)")
    parser.add_argument("--all-perform-attributes", action="store_true",
                        help="show every perform attribute, not just the default 9")
    parser.add_argument("--empty", default="-",
                        help='placeholder for empty values (default: "-")')
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    overrides = {"empty": args.empty, "mask_account_numbers": args.mask_accounts}
    if args.all_perform_attributes:
        overrides["perform_attributes"] = "all"

    suffix = ".html" if args.html else ".pdf"
    output = args.output or args.input.with_suffix(suffix)
    try:
        if args.html:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_html(args.input, **overrides), encoding="utf-8")
        else:
            render_pdf(args.input, output_path=output, **overrides)
    except CrifReportError as exc:
        print(f"crif-pdf: error: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
