# Verifying a Register

The extractor is deterministic and the review step is judgment, so a register can be wrong in three ways: a requirement is missing, a row is wrong, or a row is a duplicate or procedure text. Check each one on purpose.

## 1. Coverage: did we miss anything?

- Compare rows per division with the table of contents. Every section with technical content should have rows or a reason for having none. The report at the end of `extract.py` lists sections with no submittals article, and the skill should explain each.
- Search the PDF for the words "submit" and "submittal" in three or four sections that have zero rows. If any hit is a real requirement, the parser missed it.
- Sample the sections with the most dense requirements (mechanical, electrical, fire protection) and read the whole section once, including Parts 2 and 3. Buried requirements such as test certificates usually live there.
- Check the extractor's "not found in this PDF" list. If a whole division is missing, the manual is split into volumes, and the register is incomplete until you run the other file.

## 2. Accuracy: is each row right?

- Pick ten rows at random. For each, open the PDF at the page in the Spec Ref column and confirm the text and the type (product data, shop drawings, samples, and so on).
- Check every row marked "Added by Claude". These came from reading the manual rather than the parser, so each needs a page and a section that you can confirm.
- Read the Review Queue sheet in full. Each row states why it was flagged.

## 3. Rules: does it match the project's own procedure?

- Compare the Project Rules sheet with Section 01 33 00 (review days, resubmittal days, numbering, copies, format) and Section 01 77 00 (closeout timing).
- Make sure no procedure text sits in the register as if it were a submittal (copies, signatures, response to review).

## 4. Against a known answer

- If the team already has a register for the project, or a previous project of the same type, compare counts per division and look at every row that appears in only one list. Differences usually show either a parser miss or an item the team handled outside the spec.
- After an addendum, re-run the extractor and use `scripts/diff_drafts.py` to see what changed.

## 5. Dates

- Dates are formulas on the Register sheet. Check three rows by hand: Required Approval is the install date minus lead time minus one week, and Required Submit also subtracts review and prep time.
- Lead times are never filled in by the skill. Confirm long-lead equipment with the vendor.
