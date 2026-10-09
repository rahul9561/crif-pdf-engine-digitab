# crif-pdf-engine

Turns a Digitap **CRIF credit report JSON** response into the official-looking CRIF
**"Credit Information™ Report"** PDF (layout replicated from `samplepdf/sample.pdf`).

- Pure Python package: Jinja2 templates + CSS → PDF with **WeasyPrint**
- Fonts (Montserrat, Roboto) and the CRIF logo are **bundled** — no system fonts, no internet
- Tolerant **Pydantic v2** input models (unknown keys ignored, nulls / missing sections OK)
- No Django dependency; thread-safe, no global state → fine for Django views and Celery

```
crif_pdf_engine/
  api.py          render_pdf / render_html / parse_report / suggested_filename
  models.py       Pydantic models of the CRIF "B2C-REPORT" JSON
  mapper.py       JSON → view-model (ALL business rules & section config live here)
  formatters.py   Indian amounts, dates, codes → labels, masking
  cli.py          `crif-pdf` command
  templates/      base.html, _macros.html, sections/*.html (display only)
  static/         css/report.css, fonts/*.ttf, img/logo-crif.svg
docs/             json-schema-notes.md, pdf-layout-notes.md, field-mapping.md (+ agreed decisions)
tests/            pytest suite + fixtures/ (edge-case JSONs and their generator)
examples/         django_view.py
```

---

## 1. Install

### 1.1 System libraries for WeasyPrint (one-time, per machine)

WeasyPrint needs **Pango** (which pulls in HarfBuzz, FreeType and Fontconfig).
Python wheels do not include it.

**Ubuntu / Debian (incl. AWS EC2 Ubuntu, Docker `python:3.x-slim`)**

```bash
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libffi-dev
```

On Ubuntu 20.04 there is no `libharfbuzz-subset0` package. Leave it out of the command; recent WeasyPrint versions still work.

**Amazon Linux 2023 / RHEL / Fedora**

```bash
sudo dnf install -y pango
```

**AWS Lambda** — use a container image based on one of the images above, or a
WeasyPrint Lambda layer. The bundled fonts mean no extra font packages are needed.

**Windows 10/11** — choose one:

1. **MSYS2** (what the WeasyPrint docs recommend). Install MSYS2, then in the MSYS2 shell:
   `pacman -S mingw-w64-x86_64-pango`.
   Then, in the environment your app runs in:
   `set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin`
2. **GTK3 runtime installer** (`gtk3-runtime-x.y.z-...-win64.exe`). It adds
   `C:\Program Files\GTK3-Runtime Win64\bin` to `PATH`. This is what the development machine for this repo uses.

Check the installation:

```bash
python -m weasyprint --info
```

On Windows you may see `GLib-GIO-WARNING ... UWP app ... has no verbs` on stderr.
This is harmless noise from GLib.

### 1.2 The package

```bash
# from a checkout (editable, for development)
pip install -e ".[dev]"

# from git, in another project (e.g. Django) — or pin a tag: ...git@v0.1.0
pip install "crif-pdf-engine @ git+https://<your-git-host>/crifs-digitab.git"

# or build a wheel once and copy it around
pip wheel . --no-deps -w dist/  &&  pip install dist/crif_pdf_engine-0.1.0-py3-none-any.whl
```

Requirements: Python 3.10+, `jinja2`, `pydantic>=2`, `weasyprint>=60` (installed automatically).

---

## 2. CLI

```bash
crif-pdf input/sample.json -o output/report.pdf
crif-pdf input/sample.json --html -o output/report.html     # debug the HTML in a browser
crif-pdf report.json --mask-accounts --all-perform-attributes --empty ""
```

The exit code is `0` on success and `2` on an invalid or failed report. The error message is printed to stderr.
`python -m crif_pdf_engine.cli ...` works too.

## 3. Python

```python
from crif_pdf_engine import render_pdf, render_html, CrifReportError

pdf_bytes = render_pdf(data)                          # data: dict | JSON str | bytes | path (str/Path)
render_pdf(data, output_path="report.pdf")            # also writes the file (parent dirs created)
html = render_html(data)                              # for debugging / previews

# options (keyword overrides of crif_pdf_engine.RenderOptions)
render_pdf(
    data,
    empty="-",                         # placeholder for empty values (default "-")
    mask_account_numbers=True,         # 356305002364 -> XXXXXXXX2364 (default False)
    perform_attributes="all",          # or a list of ATTR-NAMEs; default = the 9 shown by CRIF
    generated_at=some_datetime,        # footer timestamp (default: now, IST)
)

try:
    render_pdf(data)
except CrifReportError as exc:         # subclass of ValueError
    print(exc)                         # e.g. "Report request failed: No record found (result_code=102)"
```

Accepted input shapes:

- the full Digitap envelope (`{"success":…, "data":{"report_json":{"parsed_data":{"B2C-REPORT":…}}}}`)
- `parsed_data`
- `{"B2C-REPORT": …}`
- the bare B2C-REPORT body
- a double-encoded `report_json` string

`CrifReportError` is raised for:

- invalid JSON or a missing file
- `success: false`, or a `result_code` other than 101
- `HEADER-SEGMENT.STATUS` other than `SUCCESS`
- an empty report
- input that is not a CRIF report

Other helpers:

- `suggested_filename(data)` returns e.g. `CRIF_ANAND_VARDHAN_GOYAL_CCR261006CR581766645.pdf`
- `build_context(data)` returns the template view-model, as a plain dict
- `parse_report(data)` returns the validated Pydantic model

## 4. Django

See [`examples/django_view.py`](examples/django_view.py):

```python
from django.http import HttpResponse
from crif_pdf_engine import render_pdf, suggested_filename

def crif_pdf(request, pk):
    json_data = CreditReport.objects.get(pk=pk).raw_response
    response = HttpResponse(render_pdf(json_data), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{suggested_filename(json_data)}"'
    return response
```

Rendering takes about **3–5 s for a typical 10-account report** and about **30 s for 100 accounts**
(measured on a Windows laptop; Linux is usually faster). Render large reports in a
Celery task and store the file (also shown in the example).

---

## 5. Changing the report

| You want to… | Edit |
|---|---|
| Change a label, a value, or how a field is formatted | `mapper.py` (section builders, e.g. `_account()`), helpers in `formatters.py` |
| Show more or fewer Perform Attributes | `DEFAULT_PERFORM_ATTRIBUTES` / `PERFORM_ATTRIBUTE_CATALOGUE` in `mapper.py`, or pass `perform_attributes=[...]` |
| Add a lender-type or ID-type code | `LENDER_TYPE_LABELS` / `ID_TYPE_LABELS` in `formatters.py` |
| Change colours, fonts, spacing, page margins, the footer | `static/css/report.css` (the design tokens are listed at the top) |
| Change markup or order of sections | `templates/base.html` and `templates/sections/*.html` |

**Adding a new section** (for example, "Alerts"):

1. **Model:** add the fields to `models.py`, e.g. `alerts: List[Alert] = []` on `ReportData`.
2. **Mapper:** write `_alerts(report, c)` in `mapper.py`. It should return plain strings,
   already formatted, using `c.show(value, kind)` for empty values and formatting.
   Add it to the dict returned by `build_view_model()`.
3. **Template:** create `templates/sections/alerts.html`.
   - Use the macros in `_macros.html`: `bar`, `kv_grid`, `data_table`, `history_grid`.
   - Wrap the section in `{% if r.alerts %}` to hide it when empty, or use
     `data_table(...)` to show "No records found".
   - Templates must not format values.
4. **Include** it from `base.html` at the right position.
5. **Test** it in `tests/test_api.py` (view-model) and run `pytest`.

Page-break helpers in the CSS:

- `.keep` keeps a block on one page.
- `.bar` and `.subhead` never end a page.
- Table rows never split, and table headers repeat when a table continues on the next page.

## 6. Tests

```bash
pip install -e ".[dev]"
pytest                    # full suite (~35 s, includes a 100-account render)
pytest -m "not slow"      # skip the 100-account render
python tests/fixtures/generate_fixtures.py   # regenerate edge-case fixtures from input/sample.json
```

## 7. Known limitations

- **Performance.** WeasyPrint takes about 0.3–0.5 s per page. Very large reports belong in a background job.
- **Inquiry History layout is assumed.** The sample report has no inquiries. The table
  (Lender / Date / Purpose / Ownership / Amount / Remark) follows the CRIF spec field names
  (`MEMBER-NAME`, `INQUIRY-DATE`, …) and has not yet been checked against a real report.
- **Data that is ignored.** `ALERTS`, `REQUESTED-SERVICES`, `SECURITY-DETAILS` and `LINKED-ACCOUNTS`
  are not rendered, because the reference PDF does not show them.
- **Lender-type labels** cover the common CRIF codes. An unknown code is printed as-is.
- **Score "Range"** is always blank, because the JSON does not provide it.
