# Extraction Test Log

Each manual is run through `src/specindex.py` (section index from the table of contents) and `src/extract.py` (submittal items). After every code change the earlier manuals are re-run and compared, so a fix for one manual cannot quietly break another.

## Results

| Manual | Pages | Numbering and TOC style | TOC sections located | Submittal items | Division 01 rows | Review rows |
|---|---|---|---|---|---|---|
| UTA University Center North Entry (2019) | 661 | CSI 6-digit, `SECTION 23 73 13 - TITLE` | 110 of 114 | 406 | 5 | 57 |
| Sunwatcher Clubhouse Renovations (2017) | 143 | Legacy 5-digit, no dashes in TOC | 41 of 41 | 91 | 7 | 1 |
| Gulf Bend Center 2nd and 3rd Floor (2024) | 211 | CSI 6-digit, TOC with no dashes or page numbers | 36 of 42 | 31 | 13 | 6 |
| Health Sciences Lab Drainage (2021) | 153 | CSI 6-digit, `Section` prefix and dot leaders in TOC | 35 of 40 | 45 | 36 | 0 |
| PCP Radiology Room Vol B (2023) | 355 | CSI 6-digit, `SECTION 23 3713` header, bare-letter items | 82 of 82 | 254 | 0 | 54 |
| MSU Daniel Vol I of II (2018) | 354 | Mixed legacy 5-digit Div 01 and 6-digit CSI; TOC lists both volumes | 61 of 111 (50 are Vol II) | 279 | 6 | 40 |
| StMU Garni IFC (2017) | 648 | CSI 6-digit, `SECTION 23 37 13` headers | 82 of 82 real sections (1 address line rejected) | 357 | 12 | 19 |
| WPMHC Expansion Vol 02 (2019) | 651 | CSI 6-digit, MEP-heavy | 78 of 78 | 462 | 0 | 23 |
| Bacliff Community Center (2016) | 776 | Legacy 5-digit, 1990s style, Div 01 sections discovered from body | 99 of 102 (3 absent from the file) | 440 | 10 | 42 |
| Collin County Detention Medical Addition bid packet (2023) | 171 | Front-end packet: Division 00 only, TOC lists all 234 sections of the full manual | 11 of 234 (223 not in file) | 0 | 0 | 0 |
| TxDOT Special Specification 6154 Aluminum Electrical Conductors | 3 | Single spec, numbered articles, no TOC | 1 (whole file) | 0 | 0 | 0 |
| TxDOT Special Specification 7049 Water Mains | 52 | Single spec, no TOC | 1 (whole file) | 0 | 0 | 5 |
| TxDOT Special Specification 7138 Storm Water Pump Stations | 17 | Single spec, `2. SUBMITTAL` with 2.1.1 style items | 1 (whole file) | 11 | 0 | 0 |
| Port Bolivar Fire Station RFP attachment (2012) | 2 | Request for proposal text, no specification | 0 | 0 | 0 | 0 |

Section counts include sections found in the body but not listed in the table of contents. Sections not located are front matter and contract forms (title page, table of contents, seals, AIA forms), not specification sections.

Review rows are possible submittals the parser could not place confidently: requirements found outside a submittals article, and typed items in sections that have no submittals article.

## Formats the parser handles

- Six-digit CSI numbers (`23 73 13`, `23 21 13.23`) and legacy five-digit numbers (`15120`, `099100`)
- Table of contents lines (street addresses such as `10001 Reunion Place, Ste. 200` are rejected) with or without a dash, a `Section` prefix, dot leaders or page references
- Running footers of the form `23 73 13 - 2` and `15120.1`
- Submittal articles numbered `1.03 SUBMITTALS`, `1.3 SUBMITTALS`, `4. SUBMITTALS:`, named `PLUMBING SUBMITTALS` or `ACTION SUBMITTALS`, headed `1.5 SHOP DRAWINGS`, an unnumbered `SUBMITTALS` line, or `FABRICATION DRAWINGS` in general MEP requirements
- Sections that appear in the body but not in the table of contents, and table of contents entries with the wrong number. The drainage manual lists one demolition section but contains two (`SECTION 024116` and `SECTION 024119`), and also embeds a joint sealant spec (`SECTION 321373`) that the table of contents does not list. UTA's table of contents has a typo (23 06 93 for 23 09 93). The section list follows the body headers, and the indexer notes the number the table of contents gave.
- Articles in Part 1 or Part 2, and sections that repeat an article (a second spec embedded in one section)
- Items lettered `A.` or `a.`, or a bare letter followed by spacing (`A    Product Data:`), with sub-items as `1.` or `(1)`
- A short heading item such as `A. Submittals for Review:` whose numbered children become the items
- Header and footer text that repeats across pages is detected from the document itself, with no project-specific patterns
- Page numbers follow the position of each item, so repeated text maps to the right page

## Item types

PD product data, SD shop drawings, WD wiring diagrams, SAM samples, CALC calculations, CERT certificates and qualifications, TEST test reports, WARR warranties, OM maintenance data, MOCKUP mock-ups, RECORD record drawings, SCHED schedules, REPORT surveys, statements and similar reports, REF cross-references to other sections, OTHER when no keyword matches.

## Division 01 handling

Sections that define submittal procedures (for example 01 33 00 Submittal Procedures) are tagged `Division 01 procedure` rather than mixed into the item list. Their content is project-wide rules (review time, copies, numbering, format) that the skill should apply to every row.

Requirement scans for buried submittals skip Divisions 00 and 01, where almost every mention of "submit" is contract boilerplate.

## Word files and non-specs

The scripts convert `.docx`, `.doc`, `.rtf` and `.odt` files to PDF with LibreOffice before indexing. The sample Word file (Claremore Wellness Center Bid Package 1) turned out to be a two-page bid invitation letter with no specification sections. The extractor now says so on stderr instead of returning an empty file without comment. Word conversion is not yet tested on a real specification written in Word.

## Front-end packets

The Collin County bid packet carries a table of contents for the whole project manual but only the Division 00 bidding and contract documents. It has no submittal requirements, and the extractor now says so for each of the 223 sections it cannot find. Fixing this file also exposed a table of contents bug: when the first body page opened with a `SECTION` header, the indexer read that header as the last table of contents line and skipped the section. A page that opens with a SECTION header and lists no other entries now ends the table of contents.

## Single specifications with no table of contents

State DOT style files (`Special Specification 7049 / Water Mains`) have one specification per file, numbered articles (`2. SUBMITTAL`) and decimal items (`2.1.1.`). When no table of contents or SECTION header exists, the indexer treats the file as one section named from its title block (`SS 7049`). Decimal items are parsed when an article has no lettered items, and a numbered parent with numbered children becomes the group heading. The same rule split three merged items in StMU Garni and WPMHC into their real numbered paragraphs.

In 7049 and 6154 the submittal requirements are written as sentences inside construction paragraphs (`Obtain from the manufacturer and submit to the Engineer...`), so they appear only as review rows. That is expected for this style and is the job of the Claude pass.

## Split volumes

A Vol I PDF can carry a table of contents for both volumes (MSU Daniel lists Divisions 21 to 26 that live in Vol II). The extractor now reports each such section as listed in the table of contents but not found in the PDF, so the register is not silently incomplete. Run each volume separately and combine the drafts.

## Known gaps (candidates for the Claude pass in the skill)

- Basic requirements sections in Divisions 22, 23 and 26 often carry a Submittals article that is really procedure (copies, signatures, response to review). These rows come through as items, and the Claude pass should move them to Project Rules (seen in Radiology Vol B, Bacliff 26 05 00)

- Submittals written as running prose outside any article (for example a leakage data requirement inside a ductwork products article)
- Closeout items inside general sections: warranties, as-built drawings, O&M manuals, certificates of occupancy
- Division 01 administrative submittals: pay applications, substitution requests, schedule of values, subcontractor lists
- Cross-reference lines ("See Section 16010 for submittal procedures") are typed REF and carry no content of their own
- OTHER items remain where the lead phrase has no recognizable keyword (38 in UTA, 24 in Sunwatcher, 7 in Gulf Bend, 9 in Health Sciences, 47 in Radiology Vol B, 20 in MSU Daniel, 59 in StMU Garni). Added keywords after StMU Garni: project record documents, installation instructions, analysis and delegated design, named schedules, work plans, declarations
- Some sections are skipped legitimately because they contain no submittal language at all

## Skill test

The packaged skill was run end to end on the drainage manual by following `SKILL.md`: extract, read Division 01 rules, close gaps, merge, number, build. The result is 51 submittals with 4 flagged for review. The workbook recalculates with no formula errors, the date formulas matched hand calculations, and the saved example is in `skill/submittal-register/examples/`.

## Not yet tested

- Scanned or image-only manuals (all four tested so far have a text layer)
- A real specification written in Word
- Addenda comparison (new spec version against old)
