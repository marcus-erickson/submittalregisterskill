#!/usr/bin/env python3
"""Checks that the register survives every format, and that a custom layout works.

Run from the repository root:  python3 tests/test_formats.py
Uses the example projects in submittal-register/examples. No PDFs needed.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SKILL = os.path.join(ROOT, "submittal-register")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import columns as colmod  # noqa: E402
import register_model as model  # noqa: E402
from adapters import ADAPTERS  # noqa: E402

BUILD = os.path.join(SKILL, "scripts", "build_register.py")
EX = os.path.join(SKILL, "examples")
TMP = tempfile.mkdtemp(prefix="regtest_")
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def build(*args):
    r = subprocess.run([sys.executable, BUILD, *args], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
    return r


def comparable(register):
    """Items reduced to the fields every format is expected to keep."""
    keys = ["sub_no", "rev", "section", "description", "types", "ref", "origin", "lead", "review",
            "install_date", "actual_submit", "approval_date", "status", "ball_in_court", "needs_review"]
    return [{k: it[k] for k in keys} for it in register["items"]]


for name in ("health-sciences-drainage", "radiology-volb"):
    reviewed = os.path.join(EX, f"{name}-reviewed.csv")
    rules = os.path.join(EX, f"{name}-rules.json")
    xlsx = os.path.join(TMP, f"{name}.xlsx")
    js = os.path.join(TMP, f"{name}.json")
    xlsx2 = os.path.join(TMP, f"{name}-2.xlsx")
    csv_out = os.path.join(TMP, f"{name}.csv")
    layout = colmod.load()

    check(f"{name}: build xlsx", build(reviewed, xlsx, "--rules", rules, "--save-json", js).returncode == 0)
    from_json = model.load_register(js)
    from_xlsx = ADAPTERS["xlsx"].read(xlsx, layout)

    check(f"{name}: xlsx read matches json", comparable(from_xlsx) == comparable(from_json),
          "first difference: " + str(next((a, b) for a, b in zip(comparable(from_xlsx), comparable(from_json)) if a != b)) if comparable(from_xlsx) != comparable(from_json) else "")
    check(f"{name}: rules survive xlsx round trip",
          from_xlsx["rules"].get("review_weeks") == from_json["rules"].get("review_weeks")
          and from_xlsx["rules"].get("division01_notes") == from_json["rules"].get("division01_notes"))

    check(f"{name}: xlsx -> xlsx", build(xlsx, xlsx2).returncode == 0)
    again = ADAPTERS["xlsx"].read(xlsx2, layout)
    check(f"{name}: second workbook holds the same data", comparable(again) == comparable(from_json))

    check(f"{name}: xlsx -> csv", build(xlsx, csv_out).returncode == 0)
    from_csv = ADAPTERS["csv"].read(csv_out, layout)
    # CSV is an export: it has no review flag, and it writes the project default review time
    # into each row instead of "inherit the default", so expect those two differences.
    default_review = from_json["rules"]["review_weeks"]
    expected = [{**c, "needs_review": False, "review": c["review"] if c["review"] != "" else default_review}
                for c in comparable(from_json)]
    check(f"{name}: csv read matches json (export form)", comparable(from_csv) == expected)

# a live register: statuses and dates typed into the workbook must survive a rebuild
name = "health-sciences-drainage"
reg = model.load_register(os.path.join(TMP, f"{name}.json"))
reg["items"][0].update(status="Submitted", actual_submit="2026-10-01", ball_in_court="Architect")
reg["items"][1].update(status="Approved", actual_submit="2026-09-20", approval_date="2026-10-02", install_date="2027-02-01", lead=8)
live_json = os.path.join(TMP, "live.json")
model.dump_register(reg, live_json)
live_xlsx = os.path.join(TMP, "live.xlsx")
build(live_json, live_xlsx)
back = ADAPTERS["xlsx"].read(live_xlsx, colmod.load())
# the default layout has no Ball in Court column, so that one field is not written
no_bic = lambda reg_: [{k: v for k, v in c.items() if k != "ball_in_court"} for c in comparable(reg_)]
check("live status and dates survive json -> xlsx -> read (default layout)", no_bic(back) == no_bic(reg))
check("default layout does not carry ball in court (use json as the store, or a layout with the column)",
      back["items"][0]["ball_in_court"] == "")

# custom layout: different headers, order, a custom column, ball in court
custom = os.path.join(EX, "columns-tracking.json")
custom_xlsx = os.path.join(TMP, "custom.xlsx")
reg["items"][0]["extra"] = {"x_trade": "Plumbing"}
model.dump_register(reg, live_json)
check("custom layout builds", build(live_json, custom_xlsx, "--columns", custom).returncode == 0)
clayout = colmod.load(custom)
back = ADAPTERS["xlsx"].read(custom_xlsx, clayout)
check("custom layout: ball in court and custom column round trip",
      back["items"][0]["ball_in_court"] == "Architect" and back["items"][0]["extra"].get("x_trade") == "Plumbing")
check("custom layout: header text differs from default",
      [c["header"] for c in clayout["columns"] if c["key"] == "status"] == ["Review Status"])

# a layout that drops a column a formula needs: the calculated column goes, with a warning
bad = os.path.join(TMP, "no-lead.json")
json.dump({"columns": ["sub_no", "description", "section", "install_date", "status", "required_approval"]}, open(bad, "w"))
r = build(live_json, os.path.join(TMP, "no-lead.xlsx"), "--columns", bad)
check("layout missing a formula input: warns and still builds", r.returncode == 0 and "dropping calculated column" in r.stderr)

# unknown key is a clear error, not a crash later
worse = os.path.join(TMP, "typo.json")
json.dump({"columns": ["sub_no", "descripton"]}, open(worse, "w"))
r = build(live_json, os.path.join(TMP, "typo.xlsx"), "--columns", worse)
check("unknown column key gives a clear error", r.returncode != 0 and "Unknown column key" in (r.stderr + r.stdout))

# sheets values
sheets_out = os.path.join(TMP, "sheets.json")
check("sheets values build", build(live_json, sheets_out, "--format", "sheets").returncode == 0)
payload = json.load(open(sheets_out))
reg_tab = payload["tabs"]["Register"]["values"]
check("sheets: header row then one row per submittal", len(reg_tab) == len(reg["items"]) + 1)
check("sheets: Project Rules keeps review weeks in B5 and prep weeks in B6",
      payload["tabs"]["Project Rules"]["values"][4][0].startswith("Default review")
      and payload["tabs"]["Project Rules"]["values"][5][0].startswith("Default prep"))
hdr = reg_tab[0]
row2 = dict(zip(hdr, reg_tab[2]))  # the item given an install date and lead time
check("sheets: calculated dates are formulas", str(row2["Required Submit"]).startswith("=IF("), str(row2["Required Submit"]))

# csv carries calculated dates as values. Item 2: install 2027-02-01, lead 8, review 2.14, prep 1
# = 11.14 weeks = 77.98 days before install, which floors to 78 days: 2026-11-15.
csv_live = os.path.join(TMP, "live.csv")
build(live_json, csv_live)
import csv as _csv  # noqa: E402
rows = list(_csv.DictReader(open(csv_live, encoding="utf-8")))
check("csv: required approval is install date minus lead time", rows[1]["Required Approval"] == "2026-12-07", rows[1]["Required Approval"])
check("csv: required submit subtracts lead, review and prep", rows[1]["Required Submit"] == "2026-11-15", rows[1]["Required Submit"])
check("csv: closed submittal has no days to due", rows[1]["Days to Due"] == "")

# the Python date math must agree with the formulas in the workbook, as LibreOffice calculates them
import glob, shutil  # noqa: E402
from datetime import datetime  # noqa: E402
if shutil.which("soffice"):
    src = os.path.join(EX, "radiology-volb-reviewed.csv")
    secs = []
    for r in _csv.DictReader(open(src, encoding="utf-8")):
        if r["section"] not in secs:
            secs.append(r["section"])
    inst = os.path.join(TMP, "install.csv")
    with open(inst, "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["section", "install_date", "lead_weeks"])
        for i, s_ in enumerate(secs[:40]):
            w.writerow([s_, f"2027-0{1 + i % 9}-{10 + i % 18:02d}", [0, 4, 8, 12.5, 20][i % 5]])
    x_, j_, c_ = (os.path.join(TMP, "cross" + e) for e in (".xlsx", ".json", ".csv"))
    build(src, x_, "--rules", os.path.join(EX, "radiology-volb-rules.json"), "--install-dates", inst, "--save-json", j_)
    build(j_, c_)
    subprocess.run(["soffice", "--headless", "--convert-to", "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,1", x_,
                    "--outdir", TMP], capture_output=True, timeout=170)
    lo = list(_csv.reader(open(os.path.join(TMP, "cross-Register.csv"), encoding="utf-8")))
    hi = next(i for i, r in enumerate(lo) if "Required Submit" in r)
    ci = {h: lo[hi].index(h) for h in ("Required Approval", "Required Submit", "Days to Due")}
    py = list(_csv.DictReader(open(c_, encoding="utf-8")))

    def day(v):
        v = v.strip().split(" ")[0]
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                pass
        return v

    def whole(v):
        return "" if not v.strip() else int(round(float(v)))

    bad = []
    for lr, pr in zip(lo[hi + 1:], py):
        for h in ("Required Approval", "Required Submit"):
            if day(lr[ci[h]]) != day(pr[h]):
                bad.append((pr["Sub #"], h))
        if whole(lr[ci["Days to Due"]]) != whole(pr["Days to Due"]):
            bad.append((pr["Sub #"], "Days to Due"))
    check(f"python date math matches the Excel formulas on {len(py)} rows", not bad, str(bad[:3]))
else:
    print("SKIP  date math cross-check (LibreOffice not installed)")

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("All checks passed")
