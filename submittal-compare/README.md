# Submittal Compare Skill

A Claude skill that compares two submittal registers for the same project and reports what changed in substance: submittals added, deleted, moved to another spec section, and changed in type or approval requirement.

Use it when a register has been revised, when an owner's register needs checking against one built from the specification, or when two people edited copies of the same register.

## How it works

1. You give Claude the two registers (Excel, CSV or `register.json`) and say which is old.
2. `scripts/compare_registers.py` pairs up the submittals within each spec section, then across sections for anything that moved. It ignores noise: case, plurals, punctuation, word order, abbreviations, extra detail in a description, row order and numbering. Those are counted, not listed.
3. Pairs it cannot settle (a description that changed a lot) are handed to Claude to read and decide. The decisions go back in through `--resolve`.
4. Claude writes a short summary that leads with themes (a new section, a block of items that changed type, a section that changed a lot) and groups the rest by section and type.
5. You get `Register-Comparison.xlsx` with Added, Deleted, Modified, Moved, Tracking, To confirm and Wording only sheets.

Status, dates and ball in court differences are reported on their own sheet as progress changes, so they do not bury scope changes.

## Install

Download `downloads/submittal-compare.zip` from the repository. It bundles the register readers it needs. In the repository it uses the sibling `submittal-register` folder.

## Limits

Matching is by wording inside a spec section, so an item that is both renamed and moved shows as one deleted and one added. Repeated items (the same product under several submittal types) pair in order and can land on the wrong twin. PDFs are not read. `tests/test_compare.py` checks that known edits are found and that noise is not reported. On the one real pair tried so far (an owner's 1,519-line register against one generated from the specification) the output was readable and the borderline pairs were few, but that is a single project.
