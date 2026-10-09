"""Regenerate the edge-case fixtures from input/sample.json.

    python tests/fixtures/generate_fixtures.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parents[1] / "input" / "sample.json"


def _b2c(doc: dict) -> dict:
    return doc["data"]["report_json"]["parsed_data"]["B2C-REPORT"]


def _write(name: str, doc: dict) -> None:
    (HERE / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", name)


def no_accounts(base: dict) -> dict:
    doc = copy.deepcopy(base)
    b2c = _b2c(doc)
    sd = b2c["REPORT-DATA"]["STANDARD-DATA"]
    sd["TRADELINES"] = []
    sd["EMPLOYMENT-DETAILS"] = []
    sd["DEMOGS"]["VARIATIONS"] = []
    for key in ("PRIMARY-ACCOUNTS-SUMMARY", "SECONDARY-ACCOUNTS-SUMMARY"):
        summary = b2c["REPORT-DATA"]["ACCOUNTS-SUMMARY"][key]
        for k in summary:
            summary[k] = "0"
    return doc


def null_fields(base: dict) -> dict:
    """Every scalar becomes null or "" (alternating); some lists -> null / single object."""
    doc = copy.deepcopy(base)
    counter = [0]

    def blank(node):
        if isinstance(node, dict):
            return {k: blank(v) for k, v in node.items()}
        if isinstance(node, list):
            return [blank(v) for v in node]
        counter[0] += 1
        return None if counter[0] % 2 else ""

    b2c = _b2c(doc)
    blanked = blank(b2c)
    # Keep just enough to be a valid, successful report.
    blanked["HEADER-SEGMENT"]["STATUS"] = "SUCCESS"
    blanked["HEADER-SEGMENT"]["REPORT-ID"] = "CCR000000NULLTEST"
    sd = blanked["REPORT-DATA"]["STANDARD-DATA"]
    sd["SCORE"] = None
    sd["INQUIRY-HISTORY"] = None
    sd["EMPLOYMENT-DETAILS"] = {"EMPLOYMENT-DETAIL": None}        # single object, not list
    sd["TRADELINES"][0]["HISTORY"] = None
    sd["TRADELINES"][1]["SECURITY-DETAILS"] = {"SECURITY-TYPE": None}
    blanked["REQUEST-DATA"]["APPLICANT-SEGMENT"]["DOB"] = None
    blanked["REPORT-DATA"]["TRENDS"] = None
    blanked["REPORT-DATA"]["ACCOUNTS-SUMMARY"]["MFI-GROUP-ACCOUNTS-SUMMARY"] = None
    doc["data"]["report_json"]["parsed_data"]["B2C-REPORT"] = blanked
    return doc


def many_accounts(base: dict, count: int = 100) -> dict:
    doc = copy.deepcopy(base)
    b2c = _b2c(doc)
    sd = b2c["REPORT-DATA"]["STANDARD-DATA"]
    source = sd["TRADELINES"]
    tradelines = []
    for i in range(count):
        t = copy.deepcopy(source[i % len(source)])
        t["ACCT-NUMBER"] = f"TEST{i:012d}"
        if i % 7 == 0:  # some very long grantor names to exercise wrapping
            t["CREDIT-GRANTOR"] = "THE VERY LONG NAME CO-OPERATIVE URBAN BANK LIMITED BRANCH OFFICE"
        if i % 11 == 0:
            t["CREDIT-GRANTOR-TYPE"] = "ZZZ"  # unknown lender code -> shown raw
        tradelines.append(t)
    sd["TRADELINES"] = tradelines
    sd["INQUIRY-HISTORY"] = [
        {
            "MEMBER-NAME": f"LENDER {i}",
            "INQUIRY-DATE": f"{(i % 28) + 1:02d}-0{(i % 9) + 1}-2026",
            "PURPOSE": "Personal Loan",
            "OWNERSHIP-TYPE": "Individual",
            "AMOUNT": str(50000 * (i + 1)),
            "REMARK": "",
        }
        for i in range(30)
    ]
    b2c["REPORT-DATA"]["ACCOUNTS-SUMMARY"]["PRIMARY-ACCOUNTS-SUMMARY"]["NUMBER-OF-ACCOUNTS"] = str(count)
    return doc


def failed_envelope() -> dict:
    return {
        "success": False,
        "billable": False,
        "result_code": 102,
        "message": "No record found for the given details",
        "request_id": "00000000-0000-0000-0000-000000000000",
        "data": None,
    }


def failed_header_status(base: dict) -> dict:
    doc = copy.deepcopy(base)
    _b2c(doc)["HEADER-SEGMENT"]["STATUS"] = "FAILED"
    return doc


def empty_report() -> dict:
    return {"success": True, "result_code": 101, "data": {"report_json": {"parsed_data": {"B2C-REPORT": {}}}}}


def main() -> None:
    base = json.loads(SAMPLE.read_text(encoding="utf-8"))
    _write("no_accounts.json", no_accounts(base))
    _write("null_fields.json", null_fields(base))
    _write("many_accounts_100.json", many_accounts(base))
    _write("failed_envelope.json", failed_envelope())
    _write("failed_header_status.json", failed_header_status(base))
    _write("empty_report.json", empty_report())


if __name__ == "__main__":
    main()
