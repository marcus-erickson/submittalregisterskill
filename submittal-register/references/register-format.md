# Register format from the spec

Some owners define the register columns in Division 01. Federal (UFGS) work does it in 01 33 00, paragraph 1.7 "Submittal Register", with lettered columns. Build the register's columns from that definition when it exists. When the spec says nothing about columns, use the default layout (`scripts/columns.default.json`) and tell the person that is what you used.

## Finding the definition

Search Division 01 (01 33 00, 01 33 23, 01 30 00) for "Column (a)", "Column (b)" and so on, or for "register" near "columns", "fields" or "form". Read the paragraphs that follow. Federal text spreads the definitions over several paragraphs by who fills them in (Government delivers c to f, Contractor fills a, g, h, i, and so on). Collect every lettered column from all of them.

## Mapping to keys

| Spec column (federal) | Meaning | Key |
| --- | --- | --- |
| (a) | Activity number from the schedule | `x_activity` |
| (b) | Transmittal number | `transmittal` |
| (c) | Spec section | `section` |
| (d) | Description, SD number and type | `description` (SD number is in `sd`) |
| (e) | Principal paragraph | `paragraph` |
| (f) | Not defined in the spec text, usually the G/S classification | `classification` |
| (g) | Contractor submit date | `required_submit` |
| (h) | Contractor approval date | `required_approval` |
| (i) | Date material is needed | `install_date` |
| (j), (k) | Action code and its date | `action_code`, `action_date` |
| (l) | Date transmitted or received | `actual_submit` |
| (m) to (p) | Dates of review actions | `x_review_action_1` to `x_review_action_4` |
| (q) | Approval received or returned | `approval_date` |
| (r) | Not defined in the spec text, remarks | `notes` |

Anything that has no known key becomes an `x_` custom column. Keep the spec's lettered order. `examples/columns-federal.json` is the layout built from the Charlotte ANG spec and can serve as a starting point.

## Limits

- The spec text is incomplete on its own. The form headings usually come from the register the Government attaches (Appendix A or similar). If the person has it, take the headers from it. If not, use the spec's wording and say so.
- Columns the spec leaves undefined (f and r above) are best guesses. Mark them in the summary.
- The Government often delivers the starting register. The contractor then verifies it, so a generated register is a check on the delivered one, and its c to f data should not be changed once the Government has issued it.
- Fill `sd`, `classification` and `paragraph` from the extraction when available. `paragraph` is best effort and may be blank.
