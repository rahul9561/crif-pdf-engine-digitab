# Field Mapping — PDF ⇄ JSON

## ✅ Agreed decisions (2026-10-07) — these override anything below

| # | Decision |
|---|---|
| Q1 | Empty values render as **`-`** in tables and label/value grids. Exceptions: the history month grids, where an empty month is a blank cell, and fields that are not in the JSON (rule F below). |
| Q2 | Inquiry Input also shows **DOB, PAN/IDs, Email and Address** when they are present. A row is hidden when its value is missing. |
| Q3 | The Score "Range" column stays **blank** (it is not in the JSON). |
| Q4 | Score Trend shows the **real** `TRENDS.VALUES` only. |
| Q5 / amounts | **All** amounts use Indian grouping (`25,92,764`), including the Primary, Secondary and MFI summaries (`0.0` → `0`). |
| Q6 | Perform Attributes shows only the **9** attributes from the reference. The full name → label catalogue lives in `mapper.py`, and an enable-list config selects which ones are shown. |
| Q7 | The variation "Type" column = `LOAN-TYPE-ASSOC`. The ID-variation "type" (PAN/Passport) is not in the JSON, so it is **not derived**. The ID table uses the same `LOAN-TYPE-ASSOC` column as every other variation table. |
| Q8 | Account numbers are **not masked** by default. An optional flag can turn masking on. |
| Q9 | "Lender Type #" = a readable label from `formatters.LENDER_TYPE_LABELS` (PRB → Private Bank, …). An unknown code is shown **raw**. The lender name is **never** shown here. |
| Q10 | 0 accounts → an "Account Information" bar with a "No records found" row. |
| Q11 | An Inquiry History table is rendered when `INQUIRY-HISTORY` is non-empty. |
| Q12 | The footer reads **"Page N of M"**. |
| Q13 | Reference page-break defects are fixed: headings are never orphaned, and each account block (bar + strip + status + grid) is kept on one page where it fits. History grids are kept with their sub-heading. |
| Bugs | Reference bugs are **not** replicated: the Score Trend shows only real scores, and instalment amount/frequency shows the amount alone when the frequency is null or empty (no `/null`). |
| F | Fields that are not in the JSON (score Range) are left **blank**, as in the reference. |
| Footer | "Generated: `DD-MM-YYYY HH:MM`" uses the render time in **IST (Asia/Kolkata)**, 24-hour. |
| QA | The visual comparison is done **section by section**, not page by page, because the reference PDF and the sample JSON are for different people. |
| Approved deviations | The SVG logo is drawn without the reference's grey square. Email variations may wrap after the `@`. Items in the account-info strip wrap as whole units. |
| Edge cases (added during step 7) | Variations with an empty VALUE are dropped. An unknown or blank variation type is shown under "Other Variations". Employment rows that are entirely empty are dropped. When the applicant name is empty, the "For …" line is omitted. |

`R` = `data.report_json.parsed_data["B2C-REPORT"]`, `SD` = `R.REPORT-DATA.STANDARD-DATA`, `AS` = `R.REPORT-DATA.ACCOUNTS-SUMMARY`, `T` = one item of `SD.TRADELINES[]`.

## Shared transformation rules (`formatters.py`)

| ID | Rule |
|---|---|
| **E** | Empty handling: `None`, `""`, whitespace and `"null"` → **blank** in the cell. The reference shows blank, not `-`. Configurable, see Q1 |
| **D** | Date: parse `DD-MM-YYYY` and re-emit as `DD-MM-YYYY`. Unparseable dates are passed through as they are. Then apply E |
| **AMT** | Amount: strip `,`, `₹`, spaces; parse as Decimal; round half-up to an integer; emit with Indian grouping (`25,92,764`, `81,98,100`) and no currency symbol, because the reference has none and the page says "All amounts are in INR". Non-numeric text (`XXX`) is passed through. Then apply E |
| **INT** | Count: `"0.0"` → `0`, `"10"` → `10` |
| **PCT** | Rate: `"0.0"` → `0.00`, `"7.85"` → `7.85` (2 decimal places) |
| **TRIM** | Collapse repeated whitespace and strip, e.g. `ADDRESSTEXT`, `"Self Employed "` |
| **TITLE** | ATTR-NAME → label: strip, `-` → space, Title Case, append `:` (`NUM-GRANTORS-DELINQ` → `Num Grantors Delinq:`) |
| **QTR** | Trend date `30-06-2026` → `Jun-26` |
| **MON** | History key `Jul:2026` → (year 2026, month 7) |

---

## Page 1 — Report header

| PDF field | JSON path | Transform |
|---|---|---|
| Document `<title>` / PDF metadata | `"Credit Information Report - " + full name` | |
| "For {NAME}" | `R.REQUEST-DATA.APPLICANT-SEGMENT.{FIRST,MIDDLE,LAST}-NAME` joined with a space | TRIM. Upper case, as in the source |
| Report ID | `R.HEADER-SEGMENT.REPORT-ID` | E |
| Status | `R.HEADER-SEGMENT.STATUS` | E. A value other than `SUCCESS` raises `CrifReportError` |
| Date of Issue | `R.HEADER-SEGMENT.DATE-OF-ISSUE` | D |
| Date of Request | `R.HEADER-SEGMENT.DATE-OF-REQUEST` | D |
| Product Type | `R.HEADER-SEGMENT.PRODUCT-TYPE` | E |
| Product Version | `R.HEADER-SEGMENT.PRODUCT-VER` | E |
| Footer "Generated: …" | *not in the JSON*: the time of rendering | `DD-MM-YYYY hh:mm AM/PM` in **IST** (Asia/Kolkata). Can be overridden with `generated_at=` for deterministic tests |
| Footer "Page N" | WeasyPrint `counter(page)` | |

## Inquiry Input Information

| PDF field | JSON path | Transform |
|---|---|---|
| Name | APPLICANT-SEGMENT name parts | as above |
| Gender | `gender=` render option if non-blank, else `APPLICANT-SEGMENT.GENDER` | `Male`/`Female`/`Other` (also `M`/`F`/`O`, any case) normalised; unknown values shown as sent; neither → blank |
| Phone Numbers | `APPLICANT-SEGMENT.PHONES[].VALUE` | joined with `, ` |
| *(not in ref)* Date of Birth | `APPLICANT-SEGMENT.DOB.DOB-DT` | D. See Q2 |
| *(not in ref)* PAN / ID | `APPLICANT-SEGMENT.IDS[]`, `ID07`→PAN, `ID01`→Passport, `ID02`→Voter ID, `ID03`→UID/Aadhaar, `ID04`→Others, `ID05`→Ration Card, `ID06`→Driving Licence | See Q2 |
| *(not in ref)* Email | `APPLICANT-SEGMENT.EMAILS[].EMAIL` | See Q2 |
| *(not in ref)* Address | `ADDRESSES[]`: `ADDRESSTEXT`, `CITY`, `STATE`, `PIN` | TRIM. See Q2 |

## CRIF HM Score(S) — one row per `SD.SCORE[]`

| Column | JSON path | Transform |
|---|---|---|
| Score Name | `SCORE[].NAME` | E |
| Range | **⚠ not in the JSON** | blank, as in the reference. See Q3 |
| Score | `SCORE[].VALUE` | E |
| Grade | `SCORE[].DESCRIPTION` | E |
| Scoring Factors (Up to 4 only) | `SCORE[].FACTORS[:4].DESC` | one per line |

If `SCORE` is empty, the table shows a single "No records found" row.

## Score Trend

| PDF | JSON | Transform |
|---|---|---|
| Header cells | `R.REPORT-DATA.TRENDS.DATES` split on `\|` | QTR. Order is kept (newest first) |
| `Score` row | `TRENDS.VALUES` split on `\|` | E. Aligned by index |

The section is hidden when `TRENDS` is missing or has no dates. ⚠ The reference shows `766, 17, 18, 18…`, which look like corrupted values (see Q4). We will render the actual `VALUES`.

## Primary / Secondary Account Summary

| Column | Key in `AS.PRIMARY-ACCOUNTS-SUMMARY` (or `SECONDARY-…`) | Transform |
|---|---|---|
| Number of Accounts | `NUMBER-OF-ACCOUNTS` | INT |
| Active Accounts | `ACTIVE-ACCOUNTS` | INT |
| Overdue Accounts | `OVERDUE-ACCOUNTS` | INT |
| Secured Accounts | `SECURED-ACCOUNTS` | INT (`"0.0"` → `0`) |
| UnSecured Accounts | `UNSECURED-ACCOUNTS` | INT |
| Untagged Accounts | `UNTAGGED-ACCOUNTS` | INT |
| Total Current Balance | `TOTAL-CURRENT-BALANCE` | AMT (`"0.0"` → `0`, matching the reference) |
| Total Sanctioned Amount | `TOTAL-SANCTIONED-AMT` | AMT |
| Total Disbursed Amount | `TOTAL-DISBURSED-AMT` | AMT |
| Total Amount Overdue | `TOTAL-AMT-OVERDUE` | AMT |
| *(not shown)* | `CURRENT-BALANCE-SECURED`, `CURRENT-BALANCE-UNSECURED` | not rendered, as in the reference |

The two tip lines are static text.

## MFI/Group Account Summary — `AS.MFI-GROUP-ACCOUNTS-SUMMARY` (4-column grid, in this order)

| Label | Key | Transform |
|---|---|---|
| Number Of Accounts: | `NUMBER-OF-ACCOUNTS` | INT |
| Active Accounts: | `ACTIVE-ACCOUNTS` | INT |
| Overdue Accounts: | `OVERDUE-ACCOUNTS` | INT |
| Closed Accounts: | `CLOSED-ACCOUNTS` | INT |
| No Of Other Mfis: | `NO-OF-OTHER-MFIS` | INT |
| No Of Own Mfis: | `NO-OF-OWN-MFIS` | INT |
| Total Own Current Balance: | `TOTAL-OWN-CURRENT-BALANCE` | AMT ⚠ the reference shows raw `0.0`. See Q5 |
| Total Own Installment Amt: | `TOTAL-OWN-INSTALLMENT-AMT` | AMT |
| Total Own Disbursed Amt: | `TOTAL-OWN-DISBURSED-AMT` | AMT |
| Total Own Overdue Amt: | `TOTAL-OWN-OVERDUE-AMT` | AMT |
| Total Other Current Balance: | `TOTAL-OTHER-CURRENT-BALANCE` | AMT |
| Total Other Installment Amt: | `TOTAL-OTHER-INSTALLMENT-AMT` | AMT |
| Total Other Disbursed Amt: | `TOTAL-OTHER-DISBURSED-AMT` | AMT |
| Total Other Overdue Amt: | `TOTAL-OTHER-OVERDUE-AMT` | AMT |
| Max Worst Delinquency: | `MAX-WORST-DELINQUENCY` | E (raw) |

Labels are generated from the keys with TITLE, which reproduces the reference wording exactly ("No Of Own Mfis").

## Additional Summary — `AS.ADDITIONAL-SUMMARY[]`

Label: TITLE(`ATTR-NAME`). Value: E(`ATTR-VALUE`). All items are shown in JSON order. The section is hidden if the list is empty.

## Perform Attributes — `AS.PERFORM-ATTRIBUTES[]` (whitelist of 9, in reference order)

| PDF label | ATTR-NAME | Transform |
|---|---|---|
| Inquiries In Last Six Months: | `INQUIRIES-IN-LAST-SIX-MONTHS` | E |
| Length Of Credit History (Years): | `LENGTH-OF-CREDIT-HISTORY-YEAR` | E |
| Length Of Credit History (Months): | `LENGTH-OF-CREDIT-HISTORY-MONTH` | E |
| Average Account Age (Years): | `AVERAGE-ACCOUNT-AGE-YEAR` | E |
| Average Account Age (Months): | `AVERAGE-ACCOUNT-AGE-MONTH` | E |
| New Accounts In Last Six Months: | `NEW-ACCOUNTS-IN-LAST-SIX-MONTHS` | E |
| New Delinquent Accounts In Last Six Months: | `NEW-DELINQ-ACCOUNT-IN-LAST-SIX-MONTHS` | E |
| Total Secured Outstanding: | `TOTAL-SECURED-OUTSTANDING` | AMT |
| Total Unsecured Outstanding: | `TOTAL-UNSECURED-OUTSTANDING` | AMT |

Names are matched after `.strip()` because one key has a leading space. The other **83 attributes are not shown** (see Q6). The whitelist will live in `mapper.py` as a constant so it is easy to extend.

## Personal Info Variations — `SD.DEMOGS.VARIATIONS[]`

Order and titles of the sub-tables, keyed by `TYPE`:

| Order | TYPE | Sub-heading | First column |
|---|---|---|---|
| 1 | `NAME-VARIATIONS` | Name Variations | Name |
| 2 | `EMAIL-VARIATIONS` | Email-ID Variations | Email |
| 3 | `DOB-VARIATIONS` | DOB Variations | DOB |
| 4 | `PHONE-VARIATIONS` | Phone Variations | Phone |
| 5 | `PAN-VARIATIONS`, `VOTER-ID-…`, `PASSPORT-…`, `UID-…`, `DRIVING-LICENSE-…`, `RATION-CARD-…`, `ID-VARIATIONS` | **ID Variations** (merged) | ID |
| 6 | `ADDRESS-VARIATIONS` | **Address Variations** (full section bar) | Address |
| — | any other unknown `*-VARIATIONS` | TITLE of the type | Value |

| Column | JSON | Transform |
|---|---|---|
| Value | `VARIATION[].VALUE` | TRIM, E |
| First Reported | `FIRST-REPORTED-DT` | D |
| Last Reported | `REPORTED-DT` | D |
| Type | `LOAN-TYPE-ASSOC`. ⚠ For ID rows the reference shows the ID kind ("PAN", "Passport"). See Q7 | |
| Source Indicator | `SOURCE-INDICATOR` | E |

A sub-table is hidden when its type is absent. The whole section is hidden when `VARIATIONS` is empty.

## Employment Details — `SD.EMPLOYMENT-DETAILS[].EMPLOYMENT-DETAIL`

Occupation ← `OCCUPATION` (TRIM). First Reported ← `FIRST-REPORTED-DT` (D). Last Reported ← `LAST-REPORTED-DT` (D). Type ← `ACCT-TYPE`. Source Indicator ← `SOURCE-INDICATOR`. The section is hidden if the list is empty.

## Account Information — one block per `T` (in array order)

Strip line:

| Item | JSON | Transform |
|---|---|---|
| Account Type: | `T.ACCT-TYPE` | E |
| Credit Grantor: | `T.CREDIT-GRANTOR` | E |
| Account #: | `T.ACCT-NUMBER` | as sent. No extra masking; CRIF already masks some numbers. See Q8 |
| Lender Type #: | ⚠ the reference repeats the **grantor name** here. The JSON has `T.CREDIT-GRANTOR-TYPE` (`PRB`/`NAB`). See Q9 | |
| As on #: | `T.REPORTED-DT` | D |
| Account Status: {x} | `T.ACCOUNT-STATUS` | E |

Detail grid:

| Label | JSON | Transform |
|---|---|---|
| Ownership: | `OWNERSHIP-TYPE` | E |
| Security Status: | `SECURITY-STATUS` | E |
| Disbursed Date: | `DISBURSED-DT` | D |
| Disbd Amt/High Credit: | `DISBURSED-AMT` | AMT |
| Credit Limit: | `CREDIT-LIMIT` | AMT |
| Interest Rate (%): | `INTEREST-RATE` | PCT |
| Last Payment Date: | `LAST-PAYMENT-DT` | D |
| Current Balance: | `CURRENT-BAL` | AMT |
| Cash Limit: | `CASH-LIMIT` | AMT |
| Closed Date: | `CLOSED-DT` | D |
| Last Paid Amt: | `LAST-PAID-AMOUNT` | AMT |
| InstlAmt/Freq: | `INSTALLMENT-AMT` (`"31,314/Monthly"`) | split on `/`, AMT on the amount part, rejoin. A freq of `null` or empty is dropped. (The reference prints `16,000/null`, which is a defect.) |
| Tenure(month): | `REPAYMENT-TENURE` | INT |
| Overdue Amt: | `OVERDUE-AMT` | AMT |
| Write off Date: | `WRITE-OFF-DT` | D |
| Account in Dispute: | `ACCT-IN-DISPUTE` | E |
| Account Remarks: | `ACCOUNT-REMARKS` | E |
| Principal Writeoff Amt: | `PRINCIPAL-WRITE-OFF-AMT` | AMT |
| Total Writeoff Amt: | `WRITE-OFF-AMT` | AMT |
| Settlement Amt: | `SETTLEMENT-AMT` | AMT |

History grids (from `T.HISTORY[]` by `NAME`):

| Sub-heading | NAME | Cell transform | Shown when |
|---|---|---|---|
| Payment History/Asset Classification: | `COMBINED-PAYMENT-HISTORY` | raw (`000/XXX`) | at least one non-empty value |
| High Credit / Sanctioned Amount History: | `HIGH-CREDIT-HISTORY` | AMT | at least one non-empty value |
| Current Balance History: | `CURRENT-BALANCE-HISTORY` | AMT | at least one non-empty value |
| Amount Paid History: | `AMT-PAID-HISTORY` | AMT | at least one non-empty value (so it is **hidden** for all 10 sample accounts except the last) |

Grid build: zip `DATES` and `VALUES` (dropping the trailing empty element), apply MON, then group by year in ascending order with Jan–Dec columns. Caption: `"{ACCT-NUMBER} | {ACCT-TYPE} | {CREDIT-GRANTOR}"`.

If there are no tradelines: show the "Account Information" bar with a single "No records found" row (see Q10).

## Inquiries — `SD.INQUIRY-HISTORY[]`

⚠ **Not present in the reference PDF**: the list is empty in both the reference and the sample. If the list is non-empty, I plan to render an "Inquiry History" section after the accounts and before END OF REPORT. It would use a bordered table with columns: Lender (`MEMBER-NAME`) | Date (`INQUIRY-DATE`, D) | Purpose (`PURPOSE`) | Ownership (`OWNERSHIP-TYPE`) | Amount (`AMOUNT`, AMT) | Remark (`REMARK`). See Q11.

## Static content (not data, kept in templates or constants)

- "-END OF REPORT-"
- The Appendix table (4 rows)
- The Disclaimer, the "PERFORM score…" paragraph and `customerservice@crifhighmark.com`
- The copyright line
- The tip texts

---

## JSON fields NOT shown in the PDF

These are dropped on purpose, to match the reference:

- `HEADER-SEGMENT.PREPARED-FOR/-ID`, `BATCH-ID`
- the whole `APPLICATION-SEGMENT`
- `TRENDS.RESERVED*` and `DESCRIPTION`
- the tradeline fields `CREDIT-GRANTOR-GROUP`, `INSTALLMENT-FREQUENCY`, `ORIGINAL-TERM`, `TERM-TO-MATURITY`, `ACTUAL-PAYMENT`, `OBLIGATION`, `SUIT-FILED-*`, `WRITTEN-OFF-SETTLED-STATUS`, `SECURITY-DETAILS[]`, `LINKED-ACCOUNTS[]`, `OCCUPATION`, `INCOME-*`
- 83 of the 92 perform attributes
- `REQUESTED-SERVICES`, `ALERTS`

## PDF items that CANNOT be found in the JSON ⚠

1. **Score "Range"** column: no field in the JSON (blank in the reference too).
2. **"Generated: …" timestamp**: not data, it is the render time.
3. **"Lender Type #"**: the reference shows the grantor name. The JSON only has the code `CREDIT-GRANTOR-TYPE`.
4. **ID Variations "Type" = PAN/Passport**: the sample JSON has a `PAN-VARIATIONS` group with `LOAN-TYPE-ASSOC` instead. The reference's source JSON evidently had a different shape.
5. **Score trend values `17`, `18`**: these don't look like scores. The reference's generator seems to have read the wrong field.

---

## Open questions — I need your decision on these before Step 2

| # | Question | My default if you don't specify |
|---|---|---|
| Q1 | Empty values: **blank** (as in the reference) or **"-"** (as in your spec)? | Blank in grids and history cells, matching the reference. Make it a `render_pdf(..., empty="")` option |
| Q2 | Inquiry Input: show only Name / Gender / Phone (as in the reference), or also DOB, PAN, Email and Address from the request? | Show the extra rows **only when present**. The reference input probably just didn't have them |
| Q3 | Score Range: leave blank? | Blank |
| Q4 | Score Trend: render the real `VALUES` (800, 774, …) instead of the reference's 17/18? | Real values |
| Q5 | MFI amounts: Indian-formatted (`0`), or raw (`0.0`) as in the reference? | Indian-formatted, for consistency with your "all amounts Indian" rule |
| Q6 | Perform Attributes: only the 9 from the reference, or all 92? | Only the 9 |
| Q7 | Variation "Type" column: `LOAN-TYPE-ASSOC`, or blank as in the reference? For IDs: PAN/Passport/… derived from the variation type? | `LOAN-TYPE-ASSOC`. For the merged ID table: the ID kind, e.g. "PAN" |
| Q8 | Mask account numbers or PAN ourselves (e.g. `XXXXXXXX2364`)? | No. Show them as CRIF sends them, with an optional `mask_account_numbers=True` flag |
| Q9 | "Lender Type #": repeat the grantor name (as in the reference) or show `CREDIT-GRANTOR-TYPE` (`PRB`/`NAB`)? | `CREDIT-GRANTOR-TYPE` mapped to a label (PRB → Private Bank, NAB → Nationalised Bank, …) |
| Q10 | 0 accounts: show an "Account Information — No records found" row, or hide the section? | Show "No records found" |
| Q11 | Inquiry History section when the data is present: OK with the proposed table? | Yes, as proposed |
| Q12 | Footer: "Page N" (as in the reference) or "Page N of M" (as in your spec)? | "Page N of M", in the same rotated side position |
| Q13 | Page breaks: fix the reference's orphaned headings and split account grids (keep them together)? | Yes, fix them |
