# CRIF (Digitap) JSON — Schema Notes

Source analysed: `input/sample.json` (90 KB, one Digitap CRIF "B2C" consumer report).

Conventions used below:

- **Type** is the JSON type observed. Nearly every leaf is a **string**, including numbers and amounts.
- **Empty** means the key is present with value `""`. Digitap rarely omits keys. It sends `""` instead, so the engine has to treat `""`, `null`, `"null"` and missing keys the same way.
- The root path `R` = `data.report_json.parsed_data["B2C-REPORT"]`.

---

## 1. Envelope (Digitap wrapper)

| Path | Type | Example | Notes |
|---|---|---|---|
| `success` | bool | `true` | `false` → raise `CrifReportError` |
| `billable` | bool | `true` | not rendered |
| `result_code` | int | `101` | `101` = success. Any other code → error |
| `message` | str | `"CRIF report fetched successfully"` | used in error messages |
| `request_id` | str (uuid) | | not rendered |
| `client_ref_num` | str (uuid) | | not rendered |
| `prefill` | object | `{result_code, request_id, billable}` | not rendered |
| `data.report_json.parsed_data` | object | | contains `B2C-REPORT` |
| `data.report_pdf_url` | null / str | `null` | not rendered |

The engine should also accept input that **starts at `B2C-REPORT`** or at `parsed_data`, because callers may have already unwrapped the envelope.

---

## 2. `R.HEADER-SEGMENT` (object, always present)

| Key | Type | Example | Notes |
|---|---|---|---|
| `DATE-OF-REQUEST` | str date `DD-MM-YYYY` | `06-10-2026` | |
| `PREPARED-FOR` | str | `"  "` | whitespace only. Not rendered |
| `PREPARED-FOR-ID` | str | `NBF0004149` | not rendered |
| `DATE-OF-ISSUE` | str date | `06-10-2026` | |
| `REPORT-ID` | str | `CCR261006CR581766645` | used in the filename |
| `BATCH-ID` | str | `5081512668261006` | not rendered |
| `STATUS` | str | `SUCCESS` | anything else → `CrifReportError` |
| `PRODUCT-TYPE` | str | `BBC CONSUMER SCORE` | |
| `PRODUCT-VER` | str | `2.0` | |

---

## 3. `R.REQUEST-DATA` (what the lender sent: the "Inquiry Input")

### 3.1 `APPLICANT-SEGMENT` (object)

| Key | Type | Example | Optional? |
|---|---|---|---|
| `FIRST-NAME` / `MIDDLE-NAME` / `LAST-NAME` | str | `ANAND` / `VARDHAN` / `GOYAL` | middle and last name may be empty |
| `GENDER` | str | `Male` | may be empty |
| `APPLICANT-ID` | str | `""` | empty |
| `DOB` | object | `{DOB-DT:"04-10-1995", AGE:"", AGE-AS-ON:""}` | the whole object may be missing |
| `IDS[]` | array of `{TYPE, VALUE}` | `{TYPE:"ID07", VALUE:"CAZPG3241C"}` | can be `[]`. `TYPE` is a CRIF ID code (ID07 = PAN) |
| `ADDRESSES[]` | array of `{TYPE, ADDRESSTEXT, CITY, LOCALITY, STATE, PIN, COUNTRY}` | `TYPE:"D08"`, `STATE:"PB"` | can be `[]`. `ADDRESSTEXT` has double spaces and a trailing space |
| `PHONES[]` | array of `{TYPE, VALUE}` | `{TYPE:"P01", VALUE:"9217010023"}` | can be `[]` |
| `EMAILS[]` | array of `{EMAIL}` | | can be `[]` |
| `ACCOUNT-NUMBER` | str | `""` | |

### 3.2 `APPLICATION-SEGMENT` (object)

All 13 keys are **empty strings** in the sample: `INQUIRY-UNIQUE-REF-NO`, `CREDIT-RPT-ID`, `CREDIT-RPT-TRN-DT-TM`, `CREDIT-INQ-PURPS-TYPE`, `CREDIT-INQUIRY-STAGE`, `CLIENT-CONTRIBUTOR-ID`, `BRANCH-ID`, `APPLICATION-ID`, `ACNT-OPEN-DT`, `LOAN-AMT`, `LTV`, `TERM`, `LOAN-TYPE`. None of them is rendered.

---

## 4. `R.REPORT-DATA.STANDARD-DATA`

### 4.1 `DEMOGS.VARIATIONS[]` (array, 6 items in the sample)

Each item looks like `{TYPE: str, VARIATION: [ ... ]}`. The `TYPE` values seen are:

`PHONE-VARIATIONS` (2), `PAN-VARIATIONS` (1), `NAME-VARIATIONS` (1), `ADDRESS-VARIATIONS` (5), `EMAIL-VARIATIONS` (1), `DOB-VARIATIONS` (1)

Other types CRIF can send that this sample doesn't contain: `VOTER-ID-VARIATIONS`, `PASSPORT-VARIATIONS`, `DRIVING-LICENSE-VARIATIONS`, `RATION-CARD-VARIATIONS`, `UID-VARIATIONS`, `ID-VARIATIONS`. The engine must handle any `*-VARIATIONS` type.

Each `VARIATION[]` item:

| Key | Type | Example | Notes |
|---|---|---|---|
| `VALUE` | str | `919217010023`, `ANANDVARDHAN001@GMAIL.COM` | addresses have a trailing space |
| `REPORTED-DT` | str date | `15-04-2026` | the **last** reported date |
| `FIRST-REPORTED-DT` | str date | `21-03-2026` | |
| `LOAN-TYPE-ASSOC` | str (CSV) | `Loan Against Bank Deposits,Auto Loan (Personal),Housing Loan` | can hold several values separated by commas |
| `SOURCE-INDICATOR` | str (CSV) | `PRB,PRB,NAB` | same positions as `LOAN-TYPE-ASSOC` |

### 4.2 `EMPLOYMENT-DETAILS[]` (array, 4 items)

Each item is wrapped: `{ "EMPLOYMENT-DETAIL": { OCCUPATION, FIRST-REPORTED-DT, LAST-REPORTED-DT, ACCT-TYPE, SOURCE-INDICATOR } }`. All values are strings. Dates may be empty (the reference PDF has a row with no dates).

### 4.3 `TRADELINES[]` (array, 10 items — the accounts)

41 keys per tradeline. All are strings except `TERM-TO-MATURITY` (int) and the three arrays.

| Key | Type | Sample values / notes |
|---|---|---|
| `ACCT-NUMBER` | str | `356305002364`, `LAPAT00048210367` (may already be masked by CRIF, e.g. `XXXX…5722`) |
| `CREDIT-GRANTOR` | str | `ICICI BANK LTD` (may be `XXXX` when the grantor is undisclosed) |
| `CREDIT-GRANTOR-GROUP` | str | `Category A`, `Category D` |
| `CREDIT-GRANTOR-TYPE` | str | `PRB`, `NAB` (lender-type code) |
| `ACCT-TYPE` | str | `Loan Against Bank Deposits`, `Auto Loan (Personal)`, `Housing Loan` (already a text label) |
| `REPORTED-DT` | str date | the "As on" date |
| `OWNERSHIP-TYPE` | str | `Individual`, `Joint` (others possible: `Guarantor`) |
| `ACCOUNT-STATUS` | str | `Closed`, `Active` |
| `CLOSED-DT` | str date / empty | |
| `DISBURSED-AMT` | str amount, **already Indian-formatted** | `1,11,600`, `40,00,000` |
| `DISBURSED-DT` | str date | |
| `INSTALLMENT-AMT` | str `"<amt>/<freq>"` or empty | `31,314/Monthly` |
| `CREDIT-LIMIT` / `CASH-LIMIT` | str amount / empty | |
| `CURRENT-BAL` | str amount | `0`, `25,92,764` |
| `INSTALLMENT-FREQUENCY` | str | `Monthly` / empty |
| `ORIGINAL-TERM` | str | empty |
| `TERM-TO-MATURITY` | **int** | `0` |
| `REPAYMENT-TENURE` | str integer (months) | `0`, `60`, `140` |
| `INTEREST-RATE` | str decimal | `0.0`, `7.85` |
| `ACTUAL-PAYMENT` | str | empty |
| `LAST-PAYMENT-DT` | str date / empty | |
| `OVERDUE-AMT` | str amount | `0` |
| `WRITE-OFF-AMT` | str amount | `0` |
| `PRINCIPAL-WRITE-OFF-AMT` | str / empty | |
| `SETTLEMENT-AMT` | str / empty | |
| `OBLIGATION` | str raw float | `27861.9746340937` (not rendered) |
| `HISTORY[]` | array (4 items) | see 4.3.1 |
| `ACCOUNT-REMARKS` | str / empty | |
| `SECURITY-STATUS` | str | `Secured` (the reference PDF also shows `Un-Secured`) |
| `ACCT-IN-DISPUTE` | str / empty | |
| `SUIT-FILED-WILFUL-DEFAULT-STATUS` | str | `No Suit filed` / empty |
| `WRITTEN-OFF-SETTLED-STATUS` | str / empty | |
| `WRITE-OFF-DT` | str date / empty | |
| `SECURITY-DETAILS[]` | array of 11-key objects | `SECURITY-TYPE`, `SECURITY-VALUATION` (raw `125283`, not formatted), … Not rendered in the reference PDF |
| `LINKED-ACCOUNTS[]` | array | always `[]` in the sample |
| `SUIT-FILED-DT` | str / empty | |
| `LAST-PAID-AMOUNT` | str / empty | |
| `OCCUPATION` | str | `Self Employed Professional`, `Self Employed ` (trailing space) |
| `INCOME-FREQUENCY` / `INCOME-AMOUNT` | str / empty | |

#### 4.3.1 `TRADELINES[].HISTORY[]` — month-wise series

There are always 4 objects, each `{NAME, DATES, VALUES}`:

| NAME | Length in the sample | VALUES format |
|---|---|---|
| `COMBINED-PAYMENT-HISTORY` | up to **36** months | `DPD/ASSET-CLASS`, e.g. `000/XXX`, `000/STD`, `023/XXX`, `XXX/XXX` |
| `HIGH-CREDIT-HISTORY` | up to **12** months | Indian-formatted amount |
| `CURRENT-BALANCE-HISTORY` | up to 12 | Indian-formatted amount |
| `AMT-PAID-HISTORY` | up to 12 | amount, often empty |

- `DATES` = `"Jul:2026|Jun:2026|…|"`: pipe-separated `Mon:YYYY` values, **newest first**, with a **trailing pipe**. Splitting on `|` therefore leaves an empty last element, which must be dropped.
- `VALUES` is aligned position-by-position with `DATES`. Values can be empty (`"||"`), which means "not reported".
- Values are already Indian-formatted (`7,36,700`).

### 4.4 `INQUIRY-HISTORY[]` — **empty `[]` in the sample**

The item shape is not available in this file. From the CRIF spec, items are expected to look like `{MEMBER-NAME, INQUIRY-DATE, PURPOSE, OWNERSHIP-TYPE, AMOUNT, REMARK}`. The engine will treat this as an optional, tolerant model.

### 4.5 `SCORE[]` (array, 1 item)

| Key | Type | Example |
|---|---|---|
| `NAME` | str | `PERFORM CONSUMER 2.2` |
| `VERSION` | str | empty |
| `VALUE` | str int | `800` |
| `DESCRIPTION` | str | `A` (the grade) |
| `FACTORS[]` | `{TYPE, DESC}` | `SF03` → `No/minimal missed payments in recent past` |

---

## 5. `R.REPORT-DATA.REQUESTED-SERVICES` — `[]` (not rendered)

## 6. `R.REPORT-DATA.ACCOUNTS-SUMMARY`

### 6.1 `PRIMARY-ACCOUNTS-SUMMARY` (12 keys, all str)

`NUMBER-OF-ACCOUNTS` `10`, `ACTIVE-ACCOUNTS` `1`, `OVERDUE-ACCOUNTS` `0`, `SECURED-ACCOUNTS` `10`, `UNSECURED-ACCOUNTS` `0`, `UNTAGGED-ACCOUNTS` `0`, `TOTAL-CURRENT-BALANCE` `0.0`, `CURRENT-BALANCE-SECURED` `2592764.0`, `CURRENT-BALANCE-UNSECURED` `0.0`, `TOTAL-SANCTIONED-AMT` `0.0`, `TOTAL-DISBURSED-AMT` `0.0`, `TOTAL-AMT-OVERDUE` `0`

⚠️ In this section, amounts are **raw floats as strings** (`2592764.0`), unlike tradelines which are pre-formatted. Counts are sometimes floats too (`SECONDARY.SECURED-ACCOUNTS = "0.0"`).

### 6.2 `SECONDARY-ACCOUNTS-SUMMARY` (10 keys)

Same keys as Primary, but without `CURRENT-BALANCE-SECURED` and `CURRENT-BALANCE-UNSECURED`.

### 6.3 `MFI-GROUP-ACCOUNTS-SUMMARY` (15 keys)

`NUMBER-OF-ACCOUNTS`, `ACTIVE-ACCOUNTS`, `OVERDUE-ACCOUNTS`, `CLOSED-ACCOUNTS`, `NO-OF-OTHER-MFIS`, `NO-OF-OWN-MFIS`, `TOTAL-OWN-CURRENT-BALANCE`, `TOTAL-OWN-INSTALLMENT-AMT`, `TOTAL-OWN-DISBURSED-AMT`, `TOTAL-OWN-OVERDUE-AMT`, `TOTAL-OTHER-CURRENT-BALANCE`, `TOTAL-OTHER-INSTALLMENT-AMT`, `TOTAL-OTHER-DISBURSED-AMT`, `TOTAL-OTHER-OVERDUE-AMT`, `MAX-WORST-DELINQUENCY`. All are strings, either ints or raw floats (`0.0`).

### 6.4 `ADDITIONAL-SUMMARY[]` (5 items of `{ATTR-NAME, ATTR-VALUE}`)

`NUM-GRANTORS`, `NUM-GRANTORS-ACTIVE`, `NUM-GRANTORS-DELINQ`, `NUM-GRANTORS-ONLY-PRIMARY`, `NUM-GRANTORS-ONLY-SECONDARY`

### 6.5 `PERFORM-ATTRIBUTES[]` (92 items of `{ATTR-NAME, ATTR-VALUE}`)

Data quirks to handle:

- One name has a **leading space**: `" MAX-EMI-AMOUNT"`.
- Some names contain spaces: `CD-TRADES WITHIN-6-MONTHS`, `AVG-PERCENTAGE-INCREASE-HIGH CREDIT`.
- Values are pre-formatted amounts (`25,92,764`), plain ints, DPD buckets (`000`) or **empty** (`MIN-UNSECURED-ACTIVE-ACCOUNT-AGE = ""`).
- The reference PDF shows only 9 of these attributes (see the field mapping).

## 7. `R.REPORT-DATA.TRENDS` (object — score history)

| Key | Example |
|---|---|
| `NAME` | `SCORE-HISTORY` |
| `DATES` | `30-06-2026\|31-03-2026\|…\|30-09-2023`: 12 quarter-end dates `DD-MM-YYYY`, newest first, **no** trailing pipe |
| `VALUES` | `800\|774\|800\|796…`: 12 values, aligned with `DATES` |
| `RESERVED1` | `PERFORM CONSUMER V2.2` |
| `RESERVED2/3` | empty |
| `DESCRIPTION` | `\|\|\|\|…`: 12 empty slots |

## 8. `R.REPORT-DATA.ALERTS` — `[]` (shape unknown, not rendered)

---

## Formats summary

| Kind | Format in the JSON | Notes |
|---|---|---|
| Date | `DD-MM-YYYY` | already in the display format. Validate it and pass it through |
| Month key | `Mon:YYYY` (e.g. `Jul:2026`) | history grids only |
| Quarter date (trend) | `DD-MM-YYYY` | displayed as `Mon-YY` (`Jun-26`) |
| Amount (tradelines, histories, perform attrs) | Indian-grouped string `25,92,764` | normalise by stripping commas, then re-format |
| Amount (account summaries) | raw float string `2592764.0` / `0.0` | must be converted to Indian grouping |
| Rate | `0.0`, `7.85` | displayed with 2 decimal places (`0.00`) |
| Booleans | none — flags are text (`No Suit filed`) | |
| Empty | `""` (sometimes whitespace `"  "`) | `null` only on `report_pdf_url` |
