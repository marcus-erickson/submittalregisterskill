---
name: submittal-register
description: Build a construction submittal register (Excel) from a project manual or specification PDF. Use when someone has a spec book or CSI sections and needs the list of required submittals, or says submittal log, submittal schedule or submittal register.
---

# Submittal Register

Turn a project manual (PDF) into a submittal register a project team can track from day one. A Python pass reads the structure and pulls every submittals article it can find. You then do the judgment work the script cannot: apply Division 01 rules, fill gaps, merge related items, set types, and flag anything uncertain. The result is an Excel workbook.

Never invent a requirement. Every row must trace to a spec section and page. If you are unsure, flag the row for review instead of guessing.

## What you need

- The project manual as a PDF with a text layer. If `pdftotext` returns almost nothing, the PDF is scanned. Say so and ask for a searchable copy, because this skill does not do OCR.
- Optional: install dates by spec section, so the workbook can calculate required submit dates. Ask once, near the end, and proceed without them if the person does not have them.

Work in a scratch folder. Do not edit the uploaded PDF.

## Steps

### 1. Run the extraction

```bash
python3 scripts/extract.py <manual.pdf> work/draft.csv
```

This builds a section index from the table of contents, then writes `draft.csv` with one row per submittal item. It prints counts and lists the sections where it found no submittals article. Rows carry a `source`:

- `Submittals article`: parsed from a submittals article. Mostly reliable.
- `Division 01 procedure`: text from the sections that define submittal procedures. These are rules, not register rows.
- `REVIEW: buried requirement` and `REVIEW: no article`: possible submittals the parser could not place. Each needs your decision.

Federal (UFGS) specifications list submittals as `SD-03 Product Data` followed by one item per paragraph, some ending `; G` or `; S`. The script gives each item its own row, typed from the SD number, with the marking in a `classification` column. Copy that marking into the row notes (G means Government approval, S means sustainability reporting). Rows flagged `REVIEW: sentence in SD list` are explanatory text inside a list: keep one only if it names something to submit. These manuals usually repeat an item in several SD groups (a product under SD-03, SD-04 and SD-10). Keep those as separate rows because each group is reviewed on its own.

To read any part of the manual, use the page ranges from `python3 scripts/specindex.py <manual.pdf>` and then `pdftotext -layout -f <first> -l <last> <manual.pdf> -`.

### 2. Read the project rules

Open the Division 01 submittal procedures (usually 01 33 00, 01 30 00 or 01 33 23) and the closeout section (01 77 00 or 01 70 00). Capture the rules in `work/rules.json`. See `references/division-01-rules.md` for what to look for and the exact JSON shape. At minimum record review time in weeks, numbering format, copies and format, and any initial submittals due after award.

If the manual has an owner-supplied submittal list, treat it as a cross-check only. Report disagreements with the sections actually in the manual. Do not copy it, because it is often carried over from another project.

### 3. Close the gaps

Work through these in order, reading the section text each time:

1. **Sections with no rows.** For each section the script reported, decide whether it truly has no submittals or the parser missed them. Look for submittal language in the whole section, including Parts 2 and 3 (mock-ups, test reports, certificates, samples, warranties).
2. **Review rows.** Confirm each one. Keep the real ones, delete the false ones, and keep `needs_review` set to `y` with a `review_note` for any you cannot settle.
3. **Items typed OTHER or REF.** Give OTHER items a type from `references/type-codes.md`. Delete REF rows that only point to another section, unless that section is not in the manual.
4. **Closeout.** Add rows the specs require at closeout: O&M manuals, warranties, record drawings, certificates, attic stock. Put the section that requires each one in the row.
5. **Division 01 submittals.** Add the project-level items from the rules (schedule of values, submittal schedule, subcontractor list, insurance, and so on) as their own rows under the Division 01 section that requires them.

Mark rows you add with `origin` = `Added by Claude` and a `page` so a person can check them.

### 4. Consolidate and number

- Combine items a contractor would send in one transmittal. Product data, shop drawings and wiring diagrams for the same piece of equipment usually become one row with type `PD+SD+WD`. Keep them separate when they have different timing or different reviewers.
- Keep each row's description specific: name the equipment or material and what is required. "Product data for air handling units" beats "Product data".
- Use the numbering format from the project rules. If there is none, leave `sub_no` blank and the builder will number rows `section-sequence` (for example `23 73 13-1`).

### 5. Lead times and dates

Leave `lead_weeks` blank unless the spec, the person, or the schedule states it. Never write a typical figure into the cell as if it were known. For long-lead equipment (see `references/long-lead.md`), add a note such as `Typically 12 to 20 weeks, confirm with vendor`. If the person gives install dates, write `work/install-dates.csv` with columns `section,install_date,lead_weeks`. The workbook then calculates Required Approval and Required Submit with formulas.

### 6. Build the workbook

Save your reviewed rows as `work/reviewed.csv` with these columns (extra columns are ignored):

`sub_no, section, section_title, description, types, article, page, origin, lead_weeks, review_weeks, notes, needs_review, review_note`

```bash
python3 scripts/build_register.py work/reviewed.csv work/Submittal-Register.xlsx \
  --rules work/rules.json --save-json work/register.json \
  [--install-dates work/install-dates.csv] [--columns layout.json]
```

Excel is the default, not the only option. See "Formats and layouts" below for CSV, Google Sheets and custom columns. Always keep `work/register.json` (the `--save-json` file) with the workbook: it holds the register as plain data, so the same register can be rebuilt in any format later.

Then recalculate and check for formula errors. If a recalculation script is available in your environment, run it. Otherwise open the file with LibreOffice headless and confirm no cell shows an error. The workbook has these sheets:

- **Register:** one row per submittal, with date formulas, a status dropdown and a days-to-due column.
- **Project Rules:** review and prep weeks (the Register reads these) and the project-wide requirements.
- **Review Queue:** every row still flagged for a human decision.
- **By Section:** counts and approval progress per spec section.
- **Legend:** type codes and cell colors.

### 7. Check before delivering

- Row count per division looks plausible against the table of contents. A division with sections but no rows needs an explanation.
- Ten spot checks: pick rows at random and confirm the text and page against the PDF.
- Every `Added by Claude` row has a page and a section.
- No leftover REF rows, and no Division 01 procedure text in the register.

### 8. Tell the person

Give the file, then a short summary: how many submittals, how many sections, what you added beyond the parser, what is in the Review Queue and why, and which rules you applied from Division 01. Name anything you could not determine, such as lead times or install dates.

## Formats and layouts

The register is plain data (`scripts/register_model.py`). Output formats are adapters in `scripts/adapters/`, and the columns come from a layout file. `build_register.py` converts between any of them, and it accepts a reviewed CSV, a register `.xlsx`, a register `.csv` or a `register.json` as input.

| Format | Command | Notes |
| --- | --- | --- |
| Excel | `build_register.py in work/Register.xlsx` | Default. Live date formulas, status dropdown, all five sheets. |
| JSON | `build_register.py in work/register.json` | Lossless. Keep this between sessions. |
| CSV | `build_register.py in work/Register.csv` | An export. Calculated dates are values, and the project default review time is written into each row. Not a good place to keep a register. |
| Google Sheets | `build_register.py in work/register.sheets.json --format sheets` | Writes the cell values. Create the spreadsheet, then send each tab's `values` with the Sheets connector using USER_ENTERED so formulas and dates parse. Not yet tried against a live connector. |

To change the columns, copy `scripts/columns.default.json`, edit it and pass `--columns`. A column is a key (default header and width) or an object with `key`, `header`, `width` and `aliases`. Known keys are listed in `scripts/columns.py`. Keys that start with `x_` are custom text columns, for example `x_trade`. `examples/columns-tracking.json` shows a layout with Ball in Court and a custom Trade column. Rules to remember:

- A field with no column in the layout is not written to Excel or CSV. Ball in Court, for instance, needs a layout that includes it.
- Calculated columns (required dates, days to due) are dropped with a warning if the columns they depend on are missing.
- When reading a workbook that came from somewhere else, pass a layout whose headers (or aliases) match its header row.

## Updating after an addendum

Run `extract.py` on the addendum or revised manual, then compare drafts:

```bash
python3 scripts/diff_drafts.py old/draft.csv new/draft.csv
```

It lists added, removed and changed items by section and article. Apply the changes to the reviewed file, bump the revision for changed items, and rebuild.

## Limits

- No OCR for scanned PDFs.
- The parser expects a table of contents or SECTION headers. A file with neither is treated as one specification (state DOT style). If it reports no specification sections, say so and ask for the full manual.
- If the extractor lists sections as missing from the PDF, the manual is split into volumes or the packet is front-end only. Tell the person which sections are missing and ask for the other file.
- Word files are converted with LibreOffice. If `soffice` is not installed, ask for a PDF.
- Submittals written as running prose outside a submittals article are found only if they match the buried-requirement patterns. Read the technical sections the script reports as empty.
