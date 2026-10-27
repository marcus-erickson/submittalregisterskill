# Submittal Register Skill

A Claude skill that turns a construction project manual (spec PDF) into a submittal register in Excel.

Building a register by hand means reading every spec section, finding the submittal paragraphs, and retyping each requirement. This skill does the structural work with a script and leaves the judgment calls to Claude: applying the Division 01 rules, finding requirements the script cannot see, merging related items, and flagging anything uncertain for a person to confirm.

## What you get

An Excel workbook with:

- **Register:** one row per submittal with number, description, spec section, type, page reference, install date, lead time, review and prep weeks, required approval and submit dates (live formulas), status dropdown, and days to due.
- **Project Rules:** review time, numbering format, copy counts and the project-wide requirements pulled from Division 01.
- **Review Queue:** every row that still needs a human decision, with the reason.
- **By Section:** counts and approval progress per spec section.
- **Legend:** type codes and cell colors.

`examples/` has a complete run on a public bid package: the raw extraction, the reviewed file, the rules file and the finished workbook.

## How it works

1. `scripts/extract.py` reads the table of contents, locates every section in the PDF, finds each submittals article and splits it into items. It tags rows from the Division 01 procedure sections separately, because those hold rules rather than items.
2. Claude reads the Division 01 procedures and records the project rules, then works through the gaps the script reports: sections with no rows, possible requirements buried in Parts 2 and 3, closeout items, and administrative submittals.
3. Claude merges related items, numbers them with the project's format, and writes a reviewed CSV.
4. `scripts/build_register.py` builds the workbook. The register is held as plain data first, so the same register can also be written as CSV, JSON or Google Sheets values, with the columns set by a layout file (`scripts/columns.default.json`). `tests/test_formats.py` checks that a register survives every format and that the date math matches the Excel formulas.

`SKILL.md` has the full instructions Claude follows.

## What the script handles

Tested on fifteen public documents, from a 2-page attachment to a 776-page manual, with the formats below:

- Six-digit CSI numbers (`23 73 13`) and the older five-digit style (`15120`)
- Tables of contents with or without dashes, page numbers, dot leaders or a `Section` prefix
- Submittal articles numbered `1.03 SUBMITTALS`, `4. SUBMITTALS:`, named `PLUMBING SUBMITTALS` or `ACTION SUBMITTALS`, headed `SHOP DRAWINGS`, or an unnumbered `SUBMITTALS` line
- Lettered items (`A.` or `a.`) with `1.` or `(1)` sub-items
- Sections that appear in the body but not in the table of contents, and table of contents entries with the wrong number
- Single specifications with no table of contents, such as state DOT special specifications (`Special Specification 7049`), with decimal items (`2.1.1.`)
- Lettered items with or without a period (`A.` or `A    Product Data:`) and lead-ins such as "submit certificates as listed below"
- Word files (`.docx`, `.doc`, `.rtf`, `.odt`), converted to PDF with LibreOffice
- Manuals that list sections from another volume: those sections are reported as not found in the PDF
- Page headers and footers that repeat, found from the document itself rather than from patterns tied to one project

Where the table of contents and the body disagree, the section list follows the body headers and the script notes the number the table of contents gave.

## Limits

- Needs a PDF with a text layer. Scanned manuals need OCR first. Word files (.docx) are converted with LibreOffice when it is installed.
- Expects a table of contents or `SECTION` headers in the body. A single specification with neither is treated as one section.
- A split manual (Vol I and Vol II) must be run one file at a time. The script lists every section its table of contents names that is missing from the file, so a partial register is never silent.
- Basic requirements sections in Divisions 21 to 26 often hold a submittals article that is really procedure. The skill's review step moves those into Project Rules.
- Lead times and install dates are inputs. The skill does not guess them. For long-lead equipment it adds a note with the usual range and asks you to confirm with the vendor.
- The deterministic pass misses submittals written as running prose outside any submittals article. Claude covers these by reading the sections the script reports as empty, but a person should still review the Review Queue.

## Requirements

- Python 3.9 or newer
- `pdftotext` (poppler-utils)
- `openpyxl`
- LibreOffice (`soffice`), only for Word input

## Using it

In Claude, add the `submittal-register` folder as a skill and attach a project manual. In Claude Code, put the folder under `.claude/skills/`.

To run the scripts directly:

```bash
python3 scripts/extract.py manual.pdf work/draft.csv
python3 scripts/specindex.py manual.pdf              # section index
python3 scripts/build_register.py work/reviewed.csv Register.xlsx --rules work/rules.json
python3 scripts/diff_drafts.py old/draft.csv new/draft.csv   # compare after an addendum
```

## Test data

The manuals used during development are public bid packages. They are not included here. Two worked examples are in `examples/`: the Northeast Texas Community College Health Sciences Simulation Lab Drainage Improvements project manual (KSA Engineers, 2021) and the Patient Care Pavilion Radiology Room project manual, Volume B (Primera Design Associates, 2023). Each example holds the reviewed rows, the project rules and the finished workbook. The `requirement` column quotes short excerpts of those public documents.

## Background

The process follows the extraction workflow described in Pelles, "Submittal Register in 30 Minutes" (https://www.pelles.ai/university/articles/submittal-register-30-minutes): gather the spec sections, extract the submittal requirements, clean and number them, then work out dates backward from installation.
