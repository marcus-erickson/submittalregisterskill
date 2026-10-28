#!/usr/bin/env python3
"""Checks for submittal-compare: known edits must be found, and noise must not be reported."""
import copy
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "submittal-register", "scripts"))
import register_model as model  # noqa: E402

spec = importlib.util.spec_from_file_location("cmp", os.path.join(ROOT, "submittal-compare", "scripts", "compare_registers.py"))
cmp_ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp_)

EX = os.path.join(ROOT, "submittal-register", "examples", "health-sciences-drainage-reviewed.csv")
tmp = tempfile.mkdtemp()


def save(items, name):
    reg = model.new_register("Test", items=items)
    path = os.path.join(tmp, name)
    model.dump_register(reg, path)
    return path


def run(old_path, new_path, resolve=None):
    _, old = cmp_.load(old_path, "O")
    _, new = cmp_.load(new_path, "N")
    res = cmp_.compare(old, new, 0.5, resolve or [])
    secs, themes = cmp_.roll_up(old, new, res)
    return res, secs, themes, old, new


rows = model.load_rows(EX)
model.number_rows(rows, "section")
base = save(rows, "base.json")

# 1. identical registers: nothing to report
res, *_ = run(base, base)
assert not (res["added"] or res["deleted"] or res["modified"] or res["moved"] or res["to_confirm"]), res

# 2. noise only: reorder, renumber, change case, plurals, punctuation. Nothing substantive.
noisy = copy.deepcopy(rows)
random.Random(1).shuffle(noisy)
for i, it in enumerate(noisy):
    it["sub_no"] = f"X-{i}"
    if i % 3 == 0:
        it["description"] = it["description"].upper()
    elif i % 3 == 1:
        it["description"] = it["description"].replace(",", " ;").replace(" and ", " & ")
res, *_ = run(base, save(noisy, "noisy.json"))
assert not (res["added"] or res["deleted"] or res["modified"] or res["moved"]), (len(res["added"]), len(res["deleted"]), res["modified"][:2])

# 3. known edits
new = copy.deepcopy(rows)
gone = [new.pop(5), new.pop(10), new.pop(20)]
added = [model.blank_item(section="99 99 99", section_title="Brand New Section", description="Widget calibration report", types="TEST"),
         model.blank_item(section=new[0]["section"], section_title=new[0]["section_title"], description="Seismic restraint calculations for piping", types="CALC")]
new.extend(added)
changed_type = new[2]
changed_type["types"] = "CALC" if changed_type["types"] != "CALC" else "PD"
approval = new[3]
approval["notes"] = (approval["notes"] + " Classification G").strip()
moved = new[4]
old_sec = moved["section"]
moved["section"], moved["section_title"] = "88 88 88", "Relocated"
tracked = new[6]
tracked["status"], tracked["approval_date"] = "Approved", "2026-09-01"
res, secs, themes, old, newi = run(base, save(new, "edited.json"))
assert len(res["deleted"]) == 3, [d["description"] for d in res["deleted"]]
assert {d["description"] for d in res["deleted"]} == {cmp_.short(g, 140) for g in gone}
assert len(res["added"]) == 2 and {a["description"] for a in res["added"]} == {"Widget calibration report", "Seismic restraint calculations for piping"}
kinds = [c["what"] for m in res["modified"] for c in m["changes"]]
assert kinds.count("type") == 1 and kinds.count("approval") == 1, kinds
assert len(res["moved"]) == 1 and res["moved"][0]["section_new"] == "88 88 88" and res["moved"][0]["section_old"] == old_sec
assert len(res["tracking"]) == 1 and any(t["field"] == "Status" for t in res["tracking"][0]["tracking"])
assert any(s["section"] == "99 99 99" and s["status"] == "new section" for s in secs)

# 4. a completely reworded line is offered for confirmation, and a resolution settles it
renamed = copy.deepcopy(rows)
victim = renamed[12]
victim["description"] = "Coordination drawings showing trench dimensions"
res, *_ = run(base, save(renamed, "renamed.json"))
assert len(res["deleted"]) == 1 and len(res["added"]) == 1, (res["deleted"], res["added"])
if res["to_confirm"]:
    q = res["to_confirm"][0]
    res2, *_ = run(base, save(renamed, "renamed.json"), [{"old": q["old_id"], "new": q["new_id"], "same": True}])
    assert not res2["deleted"] and not res2["added"]

# 5. the command line writes the workbook and JSON
out = subprocess.run([sys.executable, os.path.join(ROOT, "submittal-compare", "scripts", "compare_registers.py"), base,
                      os.path.join(tmp, "edited.json"), "-o", os.path.join(tmp, "r.json"), "--xlsx", os.path.join(tmp, "r.xlsx")],
                     capture_output=True, text=True)
assert out.returncode == 0, out.stderr
assert "Added 2, deleted 3" in out.stdout, out.stdout
from openpyxl import load_workbook  # noqa: E402
wb = load_workbook(os.path.join(tmp, "r.xlsx"))
assert {"Summary", "By section", "Added", "Deleted", "Modified", "Moved", "Tracking", "To confirm", "Wording only"} <= set(wb.sheetnames)
print("All checks passed")
