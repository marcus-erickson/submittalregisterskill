# Submittal Intake Skill

A Claude skill that keeps a submittal register current from email. When a submittal goes out for review or comes back approved, approved as noted, revise and resubmit or rejected, Claude reads the email, finds the matching register line, and updates its status, dates, revision and ball in court.

It works with registers built by the `submittal-register` skill and must be installed next to it, because both share the register data and the date logic.

## How it works

1. Claude reads submittal emails from Gmail and turns each one into an event: what happened, when, and which submittal it was about.
2. `scripts/intake.py match` finds the register line for each event and says how sure it is. It never picks between lines that fit equally well. Those go to a person.
3. `scripts/intake.py apply` checks that each change makes sense (a return needs a submission before it, and an approved line is not re-submitted by accident), writes it to `register.json`, and appends to an audit log. Running the same emails twice changes nothing.
4. The workbook is rebuilt from `register.json`.

`SKILL.md` has the full instructions Claude follows. `tests/test_intake.py` covers matching, resubmittals, out-of-order emails and repeat runs.

## Limits

Attachment contents are not read, only the email text and attachment file names. The matching thresholds were tuned on one register and will need adjusting on real mail.
