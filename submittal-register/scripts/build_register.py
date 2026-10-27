#!/usr/bin/env python3
"""Build or convert a submittal register.

Usage:
  build_register.py INPUT OUTPUT [--rules rules.json] [--project NAME]
                    [--review-weeks N] [--prep-weeks N] [--numbering section|sequential|compact]
                    [--install-dates dates.csv] [--columns layout.json]
                    [--format xlsx|csv|json|sheets] [--save-json register.json]

INPUT can be:
  a reviewed or draft CSV from extract.py (columns: sub_no, section, section_title,
      description, requirement, types, article, page, origin, source, lead_weeks,
      review_weeks, notes, needs_review, review_note, plus optional live columns)
  a register .xlsx written by this script, or any workbook whose headers match the layout
  a register .csv exported by this script
  a register .json (the lossless form)

OUTPUT format comes from its extension (.xlsx, .csv, .json), or from --format. Use
--format sheets to write the cell values for a Google Sheet (see adapters/sheets_adapter.py).

Columns come from scripts/columns.default.json unless --columns names another layout.
Install dates file (optional): section,install_date,lead_weeks  (dates as YYYY-MM-DD)

Because the register is plain data, the same command converts between formats:
  build_register.py Register.xlsx register.json     # keep the data between sessions
  build_register.py register.json Register.csv      # export for another system
"""
import argparse
import csv
import json
import os
import sys

import columns as colmod
import register_model as model
from adapters import ADAPTERS, EXTENSIONS


def input_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return "xlsx"
    if ext == ".json":
        return "json"
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
    # extraction CSVs use snake_case names; a register export uses the layout headers
    return "extraction" if "section" in header and "description" in header or "requirement" in header else "csv"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("out")
    ap.add_argument("--rules")
    ap.add_argument("--project")
    ap.add_argument("--review-weeks", type=float)
    ap.add_argument("--prep-weeks", type=float)
    ap.add_argument("--numbering", choices=["section", "sequential", "compact"], default="section")
    ap.add_argument("--install-dates")
    ap.add_argument("--columns", help="column layout JSON (default: columns.default.json)")
    ap.add_argument("--format", choices=sorted(ADAPTERS), help="output format (default: from the extension)")
    ap.add_argument("--save-json", help="also write the register as JSON to this path")
    ap.add_argument("--keep-div01", action="store_true",
                    help="keep rows tagged 'Division 01 procedure' (dropped by default)")
    a = ap.parse_args()

    layout = colmod.load(a.columns)
    kind = input_kind(a.input)
    try:
        if kind == "extraction":
            register = model.new_register(items=model.load_rows(a.input, a.keep_div01))
        else:
            register = ADAPTERS["csv" if kind == "csv" else kind].read(a.input, layout)
    except ValueError as e:
        sys.exit(str(e))

    rules = register["rules"]
    if a.rules:
        with open(a.rules, encoding="utf-8") as fh:
            rules.update(json.load(fh))
    if a.project:
        rules["project"] = a.project
    if a.review_weeks is not None:
        rules["review_weeks"] = a.review_weeks
    if a.prep_weeks is not None:
        rules["prep_weeks"] = a.prep_weeks
    for k, v in model.DEFAULT_RULES.items():
        rules.setdefault(k, v)
    register["project"] = rules.get("project", "")

    rows = register["items"]
    if not rows:
        sys.exit("No usable rows in the input (need section and description or requirement).")
    model.number_rows(rows, a.numbering)
    model.apply_install(rows, model.load_install(a.install_dates))

    fmt = a.format or EXTENSIONS.get(os.path.splitext(a.out)[1].lower())
    if not fmt:
        sys.exit("Cannot tell the output format from the file name. Use --format xlsx|csv|json|sheets.")
    n, q = ADAPTERS[fmt].write(register, a.out, layout)
    if a.save_json:
        model.dump_register(register, a.save_json)
    print(f"Wrote {a.out}: {n} submittals, {q} flagged for review")


if __name__ == "__main__":
    main()
