# Reading Division 01 for Register Rules

The sections that define submittal procedures (01 33 00 in current numbering, 01 30 00 or 01340 in older manuals) set rules that apply to every submittal. Closeout sections (01 77 00, 01 70 00, 01700) add more. Read both before building the register.

## What to capture

| Look for | Where it goes | Example wording |
|---|---|---|
| Review time for each submittal | `review_weeks` | "allow at least three weeks for each review" |
| Resubmittal handling | `division01_notes` | "allow time for resubmittals" |
| Numbering format | `numbering_note`, and set `sub_no` on every row | "07 09 00-1 for the first submittal, 07 09 00-1a for a resubmittal" |
| Copies and electronic format | `copies_format` | "submit electronic copies only" |
| Who submits | `division01_notes` | "all submittals go through the General Contractor" |
| Initial submittals after award | add rows under that Division 01 section | list of subcontractors, schedule of values, submittal schedule, insurance |
| Submittal schedule requirement | `division01_notes`, and add a row | "submit schedule of submittals within 20 days" |
| Closeout items | add rows | O&M manuals, warranties, record drawings, certificates, attic stock |
| Mock-up and testing requirements | add rows if they require a submittal | mock-up review, special inspection reports |

## rules.json shape

```json
{
  "project": "Project name",
  "review_weeks": 3,
  "prep_weeks": 1,
  "numbering_note": "Spec section, dash, sequence. Resubmittals add a letter: 07 09 00-1a.",
  "copies_format": "Electronic PDF only, through the General Contractor.",
  "rules_source": "Section 01 33 00 Submittal Procedures, pages 62 to 67",
  "division01_notes": [
    "Submit electronic copies only.",
    "Allow time for resubmittals when building the schedule."
  ]
}
```

`review_weeks` and `prep_weeks` feed the date formulas on the Register sheet. Use 2 for review and 1 for prep when the project is silent, and say that you assumed them.

## Numbering

If the project specifies a format, write it into every `sub_no`. If it does not, leave `sub_no` blank and the builder numbers rows `section-sequence`. Do not mix formats in one register.

## Owner-supplied submittal lists

Some manuals include a list of required submittals in the submittal procedures section. Use it only to cross-check. Compare its section numbers with the sections that exist in the manual and report the mismatches, since such lists are sometimes carried over from earlier projects.
