---
name: submittal-compare
description: Compare two submittal registers for the same project (two versions, or an owner's list against a generated one) and report what was added, deleted and changed in substance. Use when someone asks what changed between registers.
---

# Submittal Compare

Compare an old and a new submittal register for one project and tell the person what changed that matters. The script matches the two lists and throws away noise (rewording, plurals, punctuation, row order, numbering). You settle the few borderline pairs and write the summary. Do not list every small difference. The person wants the bigger picture: which submittals came or went, which moved to another spec section, and which changed in type or approval requirement.

Locate the scripts first. In the downloaded zip they are in `scripts/`. In the repository they are in `submittal-compare/scripts/`. Below, `CMP` stands for that folder.

## What you need

- Two registers for the same project, as `.xlsx`, `.csv` or `register.json` from the submittal-register skill, or a reviewed CSV from `extract.py`. Any workbook whose headers match the register layout also works (see the submittal-register skill for column layouts).
- Which one is old and which is new. Ask if it is not obvious from the file names or dates. Ask one question at a time.
- A PDF register (for example an owner's Form 4288 printout) must be turned into rows first. This skill does not read PDFs.

## Steps

### 1. Check it is the same project

Open both files and read the project name or number (the Project Rules sheet, the file name, the first rows). If they differ, stop and ask. Comparing registers from different projects produces a long, meaningless list.

### 2. Run the comparison

```bash
python3 CMP/compare_registers.py OLD NEW -o work/compare.json --xlsx work/Register-Comparison.xlsx \
  --old-label "Owner register, Rev 0" --new-label "Generated register"
```

It prints a digest: counts, then "What changed in substance". The workbook has these sheets: Summary, By section, Added, Deleted, Modified, Moved, Tracking, To confirm, Wording only.

What the script treats as a real difference:

- **Added / Deleted:** a submittal in one register with no counterpart in the other, in the same spec section.
- **Moved:** the same submittal under a different spec section.
- **Modified:** the type changed (for example PD to PD+SD), the approval marking changed (G, S or none), or the wording changed enough to be a different description.
- **Tracking:** status, dates, revision, lead time or ball in court differ. These are progress changes, not scope changes. Report them separately and only if the person cares.

What it ignores and only counts: upper or lower case, plurals, punctuation, word order, abbreviations, a description that gains a few words of detail, row order, and `sub_no` numbering.

### 3. Settle the pairs it could not

Open `to_confirm` in `work/compare.json`. Each entry is either a pair whose wording changed a lot or an old and a new item in the same section that share some words. `O12` means the 12th data row of the old register and `N30` the 30th of the new one, so open both registers and read the full descriptions and notes, then decide: same submittal reworded, or two different ones. Write `work/resolutions.json`:

```json
{"pairs": [{"old": "O12", "new": "N30", "same": true}, {"old": "O7", "new": "N9", "same": false}]}
```

Run step 2 again with `--resolve work/resolutions.json`. Do not guess. If you cannot tell, leave the pair alone and say so in the summary.

### 4. Write the summary

Lead with the picture, not the list. Use this order and stop when there is nothing to say:

1. One line with the size of the change: how many submittals in each register, how many matched, and the percentages from the digest (unchanged, modified or moved, and deleted as a share of the old register; added as a share of the new one). Always give both the counts and the percentages.
2. The themes from the digest, in plain words: whole sections added or removed, sections that changed a lot, a type or approval change that hit many items, a block of submittals that moved sections.
3. Added and deleted, grouped by spec section and type. Name individual items only when there are fewer than about 15 in a section or when one looks important (long lead equipment, a Government-approval item). Otherwise say "12 product data items added to 23 09 00".
4. Modified: group by what changed (type, approval) and give two or three examples of each group.
5. What was ignored: "86 wording-only differences" in one line, so the person knows it was looked at.
6. What you could not settle, and which side's rows are still flagged for review. The script marks these as unconfirmed.

If the rows come from a generated register, say how many of the added and deleted rows are still flagged for review in it.

### 5. Deliver

Give the person `Register-Comparison.xlsx` and the summary. Keep the JSON out of the way unless they ask.

## Limits

- Matching is by wording inside a spec section. A submittal that was renamed and moved to a different section at the same time shows as one deleted and one added.
- Items that repeat in several places (the same product under product data, samples and O&M) are paired in order, so a change to just one of them can land on the wrong twin. The type and approval columns usually show it.
- The type and approval comparison needs those columns filled in on both sides. A register with no types reports no type changes.
- It compares the register as written. It does not look at the specification to say which register is right.
