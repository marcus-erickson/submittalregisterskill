# Submittal Register Skill

Two Claude skills for construction submittals.

**submittal-register** builds a submittal register from a project manual or specification PDF. A script reads the manual's structure and pulls every submittal requirement it can find. Claude then does the judgment work: it applies the Division 01 rules, fills gaps, merges related items and flags what it is unsure about. The register is kept as plain data (`register.json`) and written out through an adapter, so Excel (with live date formulas), CSV, JSON and Google Sheets values all come from the same source. A column layout file controls which columns appear, their headers and order, and lets you add your own, such as Ball in Court or Trade.

**submittal-intake** keeps that register current. You pick the project's register and upload a transmittal or a stamped review return. Claude reads it, the matcher finds the register line, and the status, dates, revision and ball in court are updated. A document whose project does not fit the register is held back, ambiguous matches are put to you instead of guessed, uploading the same document twice changes nothing, and every change is written to an audit log.

## Try it

1. [Download the register zip](downloads/submittal-register.zip), or copy the `submittal-register` folder into your Claude skills (in Claude Code, `.claude/skills/`).
2. Attach a project manual PDF and ask for a submittal register.
3. Optionally give install dates by spec section so the workbook can calculate required submit dates.
4. When submittals start moving, [download the intake zip](downloads/submittal-intake.zip) (it bundles the register scripts it needs), choose the register and upload transmittals or stamped returns. `submittal-intake/examples/sample-documents/` has four fictional documents to try it with.

Requirements: Python 3.9 or newer, `pdftotext` (poppler-utils), `openpyxl`, and LibreOffice only if you start from a Word file.

See [submittal-register/README.md](submittal-register/README.md) and [submittal-intake/README.md](submittal-intake/README.md) for what each skill handles and its limits, and [docs/extraction-test-log.md](docs/extraction-test-log.md) for the extraction results on fifteen public manuals.

## Layout

| Path | What it holds |
|---|---|
| `submittal-register/` | The register skill: `SKILL.md`, scripts, output adapters, column layouts, worked examples |
| `submittal-intake/` | The intake skill: `SKILL.md`, the matcher and apply script, sample documents |
| `docs/` | Test log and a detailed analysis of one 661-page manual |
| `downloads/` | `submittal-register.zip` and `submittal-intake.zip`, rebuilt with `tools/build-zip.sh` after any change to either skill |
| `tests/` | `regress.py` re-runs the extractor on your own manuals and compares counts to a baseline. `test_formats.py` checks the output formats and the date math against LibreOffice. `test_intake.py` covers matching, the wrong-project check, resubmittals and repeat runs. `eval_matching.py` measures how often the matcher is right, asked or wrong |

## Status

Early. The extraction pass is tested on a range of public bid packages (legacy five-digit and six-digit CSI numbering, split volumes, state DOT special specifications). It does not read scanned PDFs, and lead times and install dates are always inputs, never guesses. Review the Review Queue sheet before relying on a register.

The intake matcher was measured on two public example registers (51 and 243 lines) with no confident wrong match, and it asks a person when lines read alike. It has not yet been tried on real project paperwork. Scanned stamps have no OCR and are read by eye, so they deserve a second look. The Google Sheets output is built to the connector's format but has not been run against a live sheet. Reading submittals from Gmail is left out on purpose until each project can be tied to its own label or sender list.

## License

MIT. The public project manuals used for testing are not included.
