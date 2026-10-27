#!/usr/bin/env python3
"""Compare two extract.py drafts (before and after an addendum).

Usage: diff_drafts.py old_draft.csv new_draft.csv
Lists items added, removed and changed, grouped by spec section.
Items are matched on section and article reference.
"""
import csv
import sys
from collections import defaultdict


def load(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("source") != "Submittals article":
                continue
            key = (r["section"], r["article"])
            n = 2
            while key in out:  # same article number repeated in one section
                key = (r["section"], f"{r['article']}#{n}")
                n += 1
            out[key] = r
    return out


def norm(s):
    return " ".join((s or "").lower().split())


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    old, new = load(sys.argv[1]), load(sys.argv[2])
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = [k for k in new if k in old and norm(new[k]["requirement"]) != norm(old[k]["requirement"])]
    sections = defaultdict(list)
    for k in added:
        sections[k[0]].append(("ADDED  ", k[1], new[k]["requirement"]))
    for k in removed:
        sections[k[0]].append(("REMOVED", k[1], old[k]["requirement"]))
    for k in changed:
        sections[k[0]].append(("CHANGED", k[1], f"{old[k]['requirement'][:120]}  ->  {new[k]['requirement'][:120]}"))
    print(f"{len(added)} added, {len(removed)} removed, {len(changed)} changed")
    for sec in sorted(sections):
        print(f"\n{sec}")
        for tag, art, text in sections[sec]:
            print(f"  {tag} {art:10} {text[:200]}")


if __name__ == "__main__":
    main()
