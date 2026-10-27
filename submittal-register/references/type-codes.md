# Submittal Type Codes

Use these codes in the `types` column. Join several with `+` when one row covers a package, for example `PD+SD`.

| Code | Meaning | Typical wording in specs |
|---|---|---|
| PD | Product data | product data, manufacturer's data, catalog cuts, data sheets, technical data |
| SD | Shop drawings | shop drawings, fabrication drawings, coordination drawings, layout drawings, dimensioned drawings |
| WD | Wiring diagrams | wiring diagrams, ladder diagrams, control diagrams |
| SAM | Samples | samples, verification samples, color charts, selection samples |
| CALC | Calculations | calculations, engineering analysis, sizing, delegated design |
| CERT | Certificates and qualifications | certificates, certifications, qualification data, affidavits, licenses |
| TEST | Test and inspection reports | test reports, field quality-control reports, mix designs, balance reports |
| WARR | Warranties | warranty, special warranty, guarantee |
| OM | Operation and maintenance data | maintenance data, O&M manuals, operating instructions, spare parts lists |
| MOCKUP | Mock-ups | mock-up, mockup, sample panel, sample installation |
| RECORD | Record drawings | record drawings, as-built drawings, record documents |
| SCHED | Schedules | schedule of values, submittal schedule, construction schedule |
| REPORT | Surveys, statements, other reports | survey, statement, photographs, inventory |
| REF | Cross-reference | "See Section 01 33 00 for submittal procedures" |
| OTHER | Not classified | resolve by reading the item |

## Judgment calls

- "Manufacturer's installation instructions" is product data (`PD`) unless the spec treats it as its own item.
- A "Design mixture" for concrete is a mix design, typed `TEST`.
- "Informational submittals" (qualifications, certificates, reports) still go in the register. Give them the right type and note `Informational`.
- A spec that says "submit shop drawings and product data" in one sentence is one package unless the spec assigns different reviewers or timing.
- REF rows are not submittals. Delete them unless the referenced section is missing from the manual.
