# Submittal Register Skill

A Claude skill that builds a construction submittal register (Excel) from a project manual or specification PDF.

A script reads the manual's structure and pulls every submittal requirement it can find. Claude then does the judgment work: it applies the Division 01 rules, fills gaps, merges related items, flags what it is unsure about, and builds a workbook with live date formulas.

## Try it

1. Copy the `submittal-register` folder into your Claude skills (in Claude Code, `.claude/skills/`).
2. Attach a project manual PDF and ask for a submittal register.
3. Optionally give install dates by spec section so the workbook can calculate required submit dates.

Requirements: Python 3.9 or newer, `pdftotext` (poppler-utils), `openpyxl`, and LibreOffice only if you start from a Word file.

See [submittal-register/README.md](submittal-register/README.md) for what the script handles and its limits, and [docs/extraction-test-log.md](docs/extraction-test-log.md) for the results on fifteen public manuals.

## Layout

| Path | What it holds |
|---|---|
| `submittal-register/` | The skill: `SKILL.md`, scripts, reference files, worked examples |
| `docs/` | Test log and a detailed analysis of one 661-page manual |
| `tests/` | `regress.py`, which re-runs the extractor on your own manuals and compares counts to a baseline |

## Status

Early. The extraction pass is tested on a range of public bid packages (legacy five-digit and six-digit CSI numbering, split volumes, state DOT special specifications). It does not read scanned PDFs, and lead times and install dates are always inputs, never guesses. Review the Review Queue sheet before relying on a register.

## License

MIT. The public project manuals used for testing are not included.
