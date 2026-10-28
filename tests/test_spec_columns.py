#!/usr/bin/env python3
"""Spec-defined columns: the federal layout round-trips through xlsx, csv and json.

Run from the repository root:  python3 tests/test_spec_columns.py
"""
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

LAYOUT = os.path.join(SKILL, "examples", "columns-federal.json")
TMP = tempfile.mkdtemp(prefix="speccols_")
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


layout = colmod.load(LAYOUT)
check("federal layout loads in spec order", [c["key"] for c in layout["columns"]][:6] ==
      ["x_activity", "transmittal", "section", "description", "paragraph", "classification"])

item = model.blank_item(
    sub_no="1", section="03 30 00", section_title="Cast-in-place concrete",
    description="SD-04 Samples: aggregate", types="SAM", sd="04", classification="G",
    paragraph="2.1", transmittal="T-001", action_code="A", action_date="2026-03-01",
    extra={"x_activity": "A1000", "x_review_action_1": "2026-03-10"})
reg = model.new_register("Test", None, [item])

for fmt in ("xlsx", "csv", "json"):
    path = os.path.join(TMP, "r." + fmt)
    ADAPTERS[fmt].write(reg, path, layout)
    back = ADAPTERS[fmt].read(path, layout)
    got = back["items"][0] if isinstance(back, dict) else back[0]
    ok = all(got.get(k) == item[k] for k in ("transmittal", "paragraph", "classification", "action_code"))
    ok = ok and got["extra"].get("x_activity") == "A1000"
    check(f"{fmt} round trip keeps spec fields", ok, str({k: got.get(k) for k in colmod.SPEC_KEYS}))

# the default layout leaves spec fields out, with no error
dflt = colmod.load()
ADAPTERS["csv"].write(reg, os.path.join(TMP, "d.csv"), dflt)
check("default layout still writes", True)

sys.exit(1 if failures else 0)
