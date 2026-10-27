# UTA Project Manual: Extraction Analysis

Source: `SampleSpecs/esbd-rfp-fm2020-001-uta-project-manual---bid-issue-2019-07-12.pdf`
Project: E.H. Hereford University Center North Entry Addition & Renovation, UT Arlington (BRW Architects, 100% CDs, July 2019)

## Document profile

| Item | Finding |
|---|---|
| Pages | 661 |
| Text layer | Clean, born-digital (Acrobat PDFMaker). No OCR needed. |
| Bookmarks | None usable, so structure must come from text |
| Table of contents | Section 00 00 10 lists every section by number and title (pages 7 to 29) |
| Sections with a `SECTION xx xx xx` header found by regex | 98 |
| Sections that carry their own SUBMITTALS article | about 80 of 98 |
| Near-empty pages | 50, mostly section dividers or blank backs, safe to skip |
| Divisions present | 00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 12, 22, 23, 26, 32 |

## Findings that shape the design

1. **Section headers are not uniform.** Most read `SECTION 23 73 13 - AIR HANDLING UNITS`, but some (for example 01 30 00, and likely 03 30 00 and 05 12 00) put the number and title on separate lines or use a different layout. Splitting by header regex alone misses sections. Use the table of contents as the authoritative section list, then locate each section's pages by number and title.

2. **Submittal articles are numbered two ways.** Division 01 uses `1.3 INITIAL SUBMITTALS`, while MEP sections use `1.03 SUBMITTALS`. The extractor must match both and also catch variants such as `ACTION SUBMITTALS` and `INFORMATIONAL SUBMITTALS`.

3. **MEP submittals are typed paragraphs.** Section 23 73 13 (Air Handling Units) lists four items in 1.03: A. Product Data, B. Shop Drawings, C. Wiring Diagrams, D. Maintenance Data. Each has a clear type and a description of required content. This is the easy case.

4. **The owner supplied an answer key, but it is unreliable.** Section 01 30 00 includes a "Submittal List" (pages 34 to 43, about 80 entries) in a table keyed by section number. Of its entries, roughly 49 carry section numbers that do not appear as sections in this manual (for example 04 20 00, 07 09 00, 08 51 00), and about 67 real sections are not on it, including all of Division 22, 23 and 26. It reads like a template carried over from another project. Some of the mismatch is my header regex missing sections, so treat these counts as approximate. It is still useful as a cross-check and a good example of why a tool should build the register from the sections themselves.

5. **Extraction from the list itself is noisy.** The PDF text splits words inside the table (`Product Da ta`, `Design Mix tures`) and some cells wrap or overlap. Do not rely on it as machine-readable truth.

6. **Division 01 sets register rules.** 01 30 00 requires review time of at least three weeks per submittal, numbering by section with a sequence suffix (`07 09 00-1`), and revision suffixes (`07 09 00-1a`, `1b`). It also lists initial submittals due within 20 days of agreement, and closeout items (warranties, certificates, O&M manuals, lab reports). These should drive numbering, default review duration and closeout rows.

7. **Mock-ups and O&M data sit outside Part 1.** Roughly 89 mentions of mock-ups and 15 of O&M manuals appear across the manual. Some are in Part 3 execution text, so scanning only the SUBMITTALS article would miss them.

## Implications for the extraction engine

- Build the section index from the table of contents, then map each section to its page range.
- Parse each section's Part 1 SUBMITTALS article into one record per lettered or numbered item.
- Separately scan Parts 2 and 3 for mock-ups, field and factory tests, and certifications that trigger a submittal.
- Pull project-wide rules from 01 30 00 and apply them (numbering format, review duration, copies, format).
- Add closeout rows from 01 70 00 and the warranty and O&M language.
- Compare against the Submittal List in 01 30 00 as a sanity check and report disagreements rather than trusting either side.

## Suggested record shape

`section_number, section_title, article_ref (e.g. 1.03.A), item_description, type (PD, SD, SAM, CALC, CERT, TEST, WARR, O&M, MOCKUP), requirement_text, page, confidence`

## Next steps

1. Write the section indexer and verify it finds every section in the table of contents.
2. Run extraction on Divisions 22, 23 and 26 and review the output by hand against pages 382 to 640.
3. Test the same code on the other three manuals to see where it breaks.
