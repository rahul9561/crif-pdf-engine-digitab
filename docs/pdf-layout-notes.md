# Reference PDF — Layout Notes

Source analysed: `samplepdf/sample.pdf`. It has 15 pages, A4 portrait (595.28 × 841.89 pt) and was produced by ReportLab. Measurements were taken with PyMuPDF from the actual drawing operators and text spans, not estimated from screenshots. All units are **pt** (1 pt = 1/72 in).

> ⚠️ **The reference PDF belongs to a different person ("GOPI K", 13 accounts) than `input/sample.json` ("ANAND VARDHAN GOYAL", 10 accounts).** The layout can be matched, but the values, page count and page breaks will differ. Visual comparison has to be structural: the same component on both sides, not the same page.

---

## 1. Global design tokens

### Colours

| Token | Hex | Used for |
|---|---|---|
| `navy` | `#1b3a6b` | section bar fill, report title, "For …" line, sub-headings, **all labels** and table-header text |
| `header-row` | `#e8edf9` | table header row fill, account-info strip fill |
| `zebra` | `#eef1f6` | fill of the even data rows (odd rows are `#ffffff`) |
| `border` | `#d4d7dc` | every rule and cell border |
| `text` | `#1f2126` | all values and table cells |
| `strip-text` | `#122747` | text in the account-info strip ("Account Type: …") |
| `muted` | `#4a4f57` | "Tip:" lines, history sub-captions, "Account Status: …" |
| `faint` | `#8a8f98` | side footer, disclaimer, copyright |
| white | `#ffffff` | section-bar title text |

### Line weights

- `0.25pt #d4d7dc` for every table row and column rule.
- `0.5pt` for the rule under "For <name>" and for the rules around "-END OF REPORT-".
- `0.75pt` for the rule closing the report-header grid. A `0.25pt` rule with a 6pt inset closes each account detail block.

### Typography (all fonts are embedded subsets)

| Element | Font | Size | Colour |
|---|---|---|---|
| Report title "Credit Information™ Report" | Montserrat **Bold** | 20 | navy |
| "For {NAME}" | Montserrat SemiBold | 9.5 | navy |
| Section bar title | Montserrat SemiBold | 10.5 | white |
| Sub-heading (Name Variations, Payment History/Asset Classification:, -END OF REPORT-) | Montserrat SemiBold | 9.5 | navy |
| "Account Status: Closed" | Montserrat SemiBold | 9.5 | muted |
| Label (e.g. `Report ID:`) and table header cell | Roboto **SemiBold** | 8 | navy |
| Value and table cell | Roboto Regular | 8 | text |
| History-grid cell (year and values) | Roboto Regular | **7.5** | text |
| Tip lines and history caption | Roboto Regular | 7.5 | muted |
| Account-info strip | Roboto Regular | 8 | strip-text |
| Side footer, disclaimer, copyright | Roboto Regular | 6.5 | faint |

Line height for 8pt text is **10.4pt** (1.3). Poppins is **not used** anywhere in the reference.

### Page geometry

- Content box: x **39.7 → 555.6** (width **515.9**), so the left and right margins are 39.7pt (14 mm).
- Top: the first element on continuation pages starts at **y ≈ 51.4**, giving a top margin of ≈ 51pt (18 mm).
- Bottom: content runs to y ≈ 790, giving a bottom margin of ≈ 50pt.
- Text inset inside cells and bars is **5pt** from the left edge of the cell (x 44.7 for content starting at 39.7).
- **Footer (every page):** text rotated 90° counter-clockwise, placed in the right margin at x ≈ 572–595 and vertically centred around y ≈ 373–415. It holds two lines:
  - `Generated: DD-MM-YYYY hh:mm AM/PM` (render time)
  - `Page N`
  - The reference prints `Page N` only, not "of Y". The spec asks for "Page X of Y". See the open questions in field-mapping.md.
- There is no running header. The logo and title appear only on page 1.

---

## 2. Reusable components

### 2.1 Section bar

A filled rectangle `#1b3a6b`, full width (515.9), **21.6pt high**. The title is Montserrat SemiBold 10.5 white, inset 5pt and vertically centred. The gap above a bar is ≈ 10pt.

### 2.2 Label/value grid (no fill, horizontal rules only)

Rows are separated by 0.25pt `#d4d7dc` rules. A single-line row is **18.4pt** high and a two-line row is 28.8pt. Text is vertically centred. Two variants:

- **4 columns** of 129pt each (label, value, label, value). Labels at x 44.7 / 302.6, values at x 173.7 / 431.6. Used by Inquiry Input, MFI/Group, Additional Summary and Perform Attributes. Labels wrap inside the 129pt column (e.g. "Length Of Credit History (Months):").
- **6 columns** of 86pt each. Labels at x 44.7 / 216.7 / 388.6, values at x 130.7 / 302.6 / 474.6. Used by the report header grid and the Account detail grid. Long values wrap: the reference wraps `CCR261006CR58173/2997` inside 86pt.
- When the item count is odd, the last row keeps the right-hand pair blank.

### 2.3 Data table (bordered)

- Header row: fill `#e8edf9`, height 18.4pt (39.2pt in the 3-line summary header), Roboto SemiBold 8 navy.
- Body rows alternate white / `#eef1f6`, starting with white. Rows are 18.4pt for one line and grow with wrapped text (address rows reach 91pt).
- Outer border and column rules: 0.25pt `#d4d7dc`. Horizontal rules: 0.25pt.
- Cells are left-aligned, except the summary tables and score trend values, which are centred.
- The **header row repeats** when a table continues on the next page (see page 5, where the Address table header is repeated without the section bar).

### 2.4 Sub-heading

Montserrat SemiBold 9.5 navy, inset 6pt (x 45.7), with ≈ 6pt below it before the table.

### 2.5 History (month) grid

- 13 columns: `Year` is **30.9** wide, then `Jan`…`Dec` at **40.4** each (sum 515.9).
- Header row is 17.6pt high with fill `#e8edf9`. Header text is Roboto SemiBold 8 navy and centred.
- Body rows are **17pt** high, zebra-striped white / `#eef1f6`, Roboto Regular **7.5**, centred.
- One row per calendar year, years **ascending**. Months with no data are blank cells.
- Above the grid, a caption in Roboto 7.5 muted: `{ACCT-NUMBER} | {ACCT-TYPE} | {CREDIT-GRANTOR}`.

### 2.6 Account-info strip

A fill `#e8edf9` placed directly under the "Account Information" bar. One or two lines of Roboto 8 `#122747`, with 4 spaces between the items:

`Account Type: X    Credit Grantor: Y    Account #: Z    Lender Type #: Y    As on #: DD-MM-YYYY`

---

## 3. Page by page (reference document)

### Page 1

1. **Logo** (raster in the reference) at (39.7, 56.5), 41.4 × 40pt.
2. **Title** "Credit Information™ Report", Montserrat Bold 20 navy, x 91.1, top ≈ 52.
3. "For GOPI K", Montserrat SemiBold 9.5, x 91.1, y ≈ 90.
4. A 0.5pt rule at y 106.2 (x 45.7 → 549.6, inset 6pt).
5. **Report header grid** (6 columns, 2 rows):
   - Row 1: `Report ID:` | `Status:` | `Date of Issue:`
   - Row 2: `Date of Request:` | `Product Type:` | `Product Version:`
   - Each row is 28.8pt high because values wrap. A 0.75pt rule follows at y 174.6.
6. **Section "Inquiry Input Information"** (4-column grid): `Name:` / `Gender:` / `Phone Numbers:`.
7. **Section "CRIF HM Score(S)"** (table):
   - Columns: Score Name **113.5** | Range **46.4** | Score **46.4** | Grade **51.6** | Scoring Factors (Up to 4 only) **258.0**.
   - The factors cell holds one factor description per line.
8. **Section "Score Trend"** (table):
   - First column `Retro Date` is 51.6 wide. The 12 quarter columns are 38.7 each, with headers in `Mon-YY` format (`Jun-26` … `Sep-23`), newest first, left → right.
   - A single body row: `Score` followed by 12 values, centred.
9. **Section "Primary Account Summary"**:
   - Two tip lines (7.5 muted):
     - "Tip: Current Balance & Disbursed Amount is considered ONLY for ACTIVE accounts."
     - "Tip: All amounts are in INR."
   - Then a 10-column table (51.6 each) with 3-line centred headers: Number of Accounts | Active Accounts | Overdue Accounts | Secured Accounts | UnSecured Accounts | Untagged Accounts | Total Current Balance | Total Sanctioned Amount | Total Disbursed Amount | Total Amount Overdue.
   - One centred value row.
10. **Section "Secondary Account Summary"**: identical to Primary, including the tips.
11. The page ends with whitespace (≈ 190pt). The reference lets **MFI/Group** start on a new page, apparently because the whole block did not fit.

### Page 2

1. **"MFI/Group Account Summary"** (4-column grid, 15 items in 8 rows). Values are shown **raw** (`0.0`, `0`).
2. **"Additional Summary"** (4-column grid, 5 items). Labels are Title Case versions of the ATTR-NAME.
3. **"Perform Attributes"** (4-column grid, 9 selected items).
4. **"Personal Info Variations"**:
   - Tip line: "Tip: These are applicant's personal information variations as contributed by various financial institutions."
   - Then sub-heading **Name Variations** with a table of 5 equal columns (103.2 each): Name | First Reported | Last Reported | Type | Source Indicator.
   - Then **Email-ID Variations**, with first column "Email".

### Page 3

Sub-tables continue in this order: **DOB Variations** (DOB), **Phone Variations** (Phone), **ID Variations** (ID). In ID Variations, Type is filled with "PAN" / "Passport". The rest of the page is blank because the Address table is moved to the next page.

### Pages 4–5

1. **"Address Variations"** is rendered as a full **section bar**, not a sub-heading. Table columns: Address | First Reported | Last Reported | Type | Source Indicator.
   - Addresses wrap within 103pt and rows grow to fit.
   - The table runs over two pages and the header row is repeated at the top of page 5.
2. **"Employment Details"** (section bar): Occupation | First Reported | Last Reported | Type | Source Indicator (5 equal columns).
3. **"Account Information"** for the first tradeline begins.

### Pages 5–14 — one block per tradeline (repeats 13×)

1. Section bar "Account Information".
2. Account-info strip (`#e8edf9`).
3. "Account Status: {status}" (Montserrat SemiBold 9.5 **muted**), x 45.7.
4. **6-column detail grid, 7 rows** (labels are exact):

   | col 1 | col 2 | col 3 |
   |---|---|---|
   | Ownership: | Security Status: | Disbursed Date: |
   | Disbd Amt/High Credit: | Credit Limit: | Interest Rate (%): |
   | Last Payment Date: | Current Balance: | Cash Limit: |
   | Closed Date: | Last Paid Amt: | InstlAmt/Freq: |
   | Tenure(month): | Overdue Amt: | Write off Date: |
   | Account in Dispute: | Account Remarks: | Principal Writeoff Amt: |
   | Total Writeoff Amt: | Settlement Amt: | *(empty)* |

   The grid is closed by an inset 0.25pt rule (x 45.7 → 549.6).
5. Sub-heading "**Payment History/Asset Classification:**" with a caption and a history grid (36 months, DPD/asset class).
6. Sub-heading "**High Credit / Sanctioned Amount History:**" with a caption and a grid. *Omitted if every value is empty.*
7. Sub-heading "**Current Balance History:**" with a caption and a grid. *Omitted if every value is empty.*
8. Sub-heading "**Amount Paid History:**" with a caption and a grid. *Omitted if every value is empty.* It is shown when the values are `0` (page 12), so "empty" means blank strings, not zero.

Order of the account blocks: the same order as the `TRADELINES` array.

### Page 15

1. "-END OF REPORT-" (Montserrat SemiBold 9.5 navy), centred between two 0.5pt rules (y 51.9 and 74.7).
2. **"Appendix"** section with a table: Section **113.5** | Code **82.5** | Description **319.9**. It has 4 static rows:
   - Account Summary / Number of Delinquent Accounts / Indicates number of accounts that the applicant has defaulted on within the last 6 months
   - Account Information - Credit Grantor / XXXX / Name of grantor undisclosed as credit grantor is different from inquiring institution
   - Payment History / Asset Classification / STD / Account Reported as STANDARD Asset
   - Payment History / Asset Classification / XXX / Data not reported by institution

   The Appendix rows are **not** zebra-striped: all rows are white.
3. Disclaimer paragraph (6.5 faint, 8.5pt leading), then the "PERFORM score…" paragraph and the email address, then the centred copyright line "Copyrights reserved (c) 2021 CRIF High Mark Credit Information Services Pvt Ltd".

---

## 4. Page-break behaviour observed in the reference (and defects to fix)

| Observed in reference | Plan |
|---|---|
| Table header rows repeat across pages | ✅ replicate (`thead` + `display: table-header-group`) |
| Data rows are never split | ✅ replicate (`break-inside: avoid` on `tr`) |
| **Sub-headings orphaned at the page bottom** (pp. 6, 9, 11, 12: "Payment History/Asset Classification:" plus its caption, with the grid on the next page) | ❌ defect. Keep each heading with its grid (`break-after: avoid` plus a wrapper with `break-inside: avoid`) |
| **Account detail grid split across pages** (pp. 7→8, 8→9, 10→11) and an "Account Information" bar with only one row at the page bottom | ❌ defect. Keep bar + strip + status + detail grid together |
| Address Variations moved to a new page, leaving page 3 two-thirds empty | Keep the bar with the first rows, but allow the table to break |

## 5. Assets

- Logo: the reference uses a raster version of the near-square CRIF logo with the "Together to the next level" tagline (41.4 × 40pt). `assets/logo-crif.svg` is **144 × 64** (aspect ratio 2.25). It will be drawn at a height of about 40pt (≈ 90pt wide), which pushes the title right. Alternatively, the title can be kept at x 91 by drawing the logo ≈ 46pt wide. I'll decide this visually in Step 7.
- Fonts needed: Montserrat Bold and SemiBold, Roboto Regular and SemiBold (the static TTFs exist in `assets/`). Poppins is not needed and will not be packaged unless you want it.
