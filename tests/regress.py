#!/usr/bin/env python3
"""Regression check for the extractor.

Runs extract.py on every manual listed in tests/manuals.json and compares the counts
to tests/baseline.json. Run it after every change to the scripts. A change in a count is
not necessarily a bug, but each one should be looked at with scripts/diff_drafts.py.

Usage:
    cp tests/manuals.example.json tests/manuals.json   # then edit the paths
    python3 tests/regress.py            # compare with the baseline
    python3 tests/regress.py --save     # write the current counts as the new baseline
"""
import csv, json, os, subprocess, sys, tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "..", "submittal-register", "scripts", "extract.py")
MANUALS = os.path.join(HERE, "manuals.json")
BASELINE = os.path.join(HERE, "baseline.json")

if not os.path.exists(MANUALS):
    sys.exit("Create tests/manuals.json first (see tests/manuals.example.json).")
manuals = json.load(open(MANUALS))
base = json.load(open(BASELINE)) if os.path.exists(BASELINE) else {}
cur = {}
for name, pdf in manuals.items():
    out = os.path.join(tempfile.mkdtemp(prefix="reg_"), name + ".csv")
    r = subprocess.run([sys.executable, EXTRACT, pdf, out], capture_output=True, text=True)
    if r.returncode:
        print(name, "FAILED", r.stderr[-300:])
        continue
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    c = Counter(x["source"] for x in rows)
    items = [x for x in rows if x["source"] == "Submittals article"]
    cur[name] = dict(items=c["Submittals article"], div01=c["Division 01 procedure"],
                     review=c["REVIEW: buried requirement"] + c["REVIEW: no article"],
                     other=sum("OTHER" in x["types"] for x in items))
for name, v in cur.items():
    b = base.get(name)
    flag = "" if not b else ("  SAME" if b == v else f"  CHANGED (was {b})")
    print(f"{name:20} items={v['items']:4} div01={v['div01']:3} review={v['review']:3} other={v['other']:3}{flag}")
if "--save" in sys.argv:
    json.dump(cur, open(BASELINE, "w"), indent=1)
    print("baseline saved")
