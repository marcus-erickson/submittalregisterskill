# Submittal Intake Skill

A Claude skill that keeps a submittal register current from submittal documents. When a submittal goes out for review or comes back approved, approved as noted, revise and resubmit or rejected, you upload the transmittal or the stamped return. Claude reads it, finds the matching register line, and updates its status, dates, revision and ball in court.

It works with registers built by the `submittal-register` skill and must be installed next to it, because both share the register data and the date logic.

## How it works

1. You choose the project by choosing its register, then upload the documents. One upload can list several submittals.
2. Claude reads each document and turns it into events: what happened, when, and which submittal it was about.
3. `scripts/intake.py match` finds the register line for each event and says how sure it is. It never picks between lines that fit equally well, and it holds back a document whose project name does not fit the register. Those go to you.
4. `scripts/intake.py apply` checks that each change makes sense (a return needs a submission before it, and an approved line is not re-submitted by accident), writes it to `register.json`, and appends to an audit log. Uploading the same document twice changes nothing.
5. The workbook is rebuilt from `register.json`.

`SKILL.md` has the full instructions Claude follows. `tests/test_intake.py` covers matching, the wrong-project check, resubmittals, out-of-order documents and repeat runs.

## Limits

No OCR, so scanned stamps are read by eye and worth a second look. Reading from Gmail is left out on purpose until each project can be tied to its own label or sender list. The matching thresholds were tuned on one register and will need adjusting on real documents.
