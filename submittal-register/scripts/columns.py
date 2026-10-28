#!/usr/bin/env python3
"""Column layout for register output and input.

The layout says which columns a register has, what they are called, and in what order.
It lives in a small JSON file so a different company or project can use its own layout
without editing any script. The default layout is columns.default.json.

Layout file:

    {"columns": ["sub_no", "description", {"key": "status", "header": "Review Status", "width": 20}],
     "freeze_after": "description",
     "print_through": "status"}

A column is either a key (default header and width) or an object with key, header, width and
aliases. Aliases are other header texts accepted when reading a register back in.

Known keys are listed in KEYS. Keys that start with x_ are custom text columns, kept in
item["extra"]. Calculated columns (required_approval, required_submit, days_to_due) are dropped
with a warning when a column they depend on is missing from the layout.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(HERE, "columns.default.json")

# key: (default header, default width)
KEYS = {
    "sub_no": ("Sub #", 14),
    "rev": ("Rev", 5),
    "description": ("Description", 58),
    "section": ("Spec Section", 12),
    "section_title": ("Section Title", 26),
    "types": ("Type", 11),
    "ref": ("Spec Ref", 14),
    "install_date": ("Install Date", 12),
    "lead": ("Lead Time (wk)", 10),
    "review": ("Review (wk)", 9),
    "prep": ("Prep (wk)", 9),
    "required_approval": ("Required Approval", 12),
    "required_submit": ("Required Submit", 12),
    "actual_submit": ("Actual Submit", 12),
    "approval_date": ("Approval Date", 12),
    "status": ("Status", 17),
    "days_to_due": ("Days to Due", 9),
    "origin": ("Origin", 22),
    "notes": ("Notes", 34),
    "full": ("Spec Text", 60),
    "ball_in_court": ("Ball in Court", 16),
    # fields a spec's register-format paragraph commonly defines (plain text columns)
    "line_no": ("Item No", 7),
    "sd": ("SD No", 7),
    "classification": ("Classification", 14),
    "paragraph": ("Spec Paragraph", 12),
    "transmittal": ("Transmittal No", 14),
    "action_code": ("Action Code", 9),
    "action_date": ("Action Date", 12),
}
# Plain text keys stored directly on the item (not in item["extra"]).
SPEC_KEYS = ("line_no", "sd", "classification", "paragraph", "transmittal", "action_code", "action_date")
DATE_KEYS = ("install_date", "actual_submit", "approval_date", "required_approval", "required_submit")
FORMULA_DEPS = {
    "required_approval": ("install_date", "lead"),
    "required_submit": ("install_date", "lead", "review", "prep"),
    "days_to_due": ("required_submit", "status"),
}
# Columns the register cannot be read back without.
CORE = ("section", "description")
# Extra header texts accepted on input, besides the layout header and the key itself.
BUILTIN_ALIASES = {
    "sub_no": ["submittal no", "submittal number", "sub no", "no."],
    "description": ["submittal description", "item", "title"],
    "section": ["section", "spec section no", "csi section"],
    "types": ["submittal type", "types"],
    "ref": ["spec reference", "reference"],
    "lead": ["lead time", "lead weeks", "lead_weeks"],
    "review": ["review weeks", "review_weeks", "review time"],
    "full": ["requirement", "spec text", "specification text"],
    "ball_in_court": ["bic", "ball-in-court"],
    "status": ["review status"],
}


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def custom_header(key):
    return key[2:].replace("_", " ").title()


def _column(spec):
    if isinstance(spec, str):
        spec = {"key": spec}
    key = spec["key"]
    if key not in KEYS and not key.startswith("x_"):
        sys.exit(f"Unknown column key '{key}'. Known keys: {', '.join(KEYS)}, or x_name for a custom column.")
    header, width = KEYS.get(key, (custom_header(key), 20))
    return {
        "key": key,
        "header": spec.get("header", header),
        "width": spec.get("width", width),
        "aliases": list(spec.get("aliases", [])),
    }


def load(path=None):
    """Load a layout. With no path, the default layout."""
    with open(path or DEFAULT_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    cols, seen = [], set()
    for spec in raw["columns"]:
        c = _column(spec)
        if c["key"] in seen:
            sys.exit(f"Column '{c['key']}' appears twice in the layout.")
        seen.add(c["key"])
        cols.append(c)
    keys = [c["key"] for c in cols]
    changed = True
    while changed:  # a calculated column can depend on another one, so repeat until stable
        changed = False
        for k, deps in FORMULA_DEPS.items():
            missing = [d for d in deps if d not in keys]
            if k in keys and missing:
                print(f"Warning: dropping calculated column '{k}' because the layout has no "
                      f"{', '.join(missing)} column.", file=sys.stderr)
                cols = [c for c in cols if c["key"] != k]
                keys = [c["key"] for c in cols]
                changed = True
    layout = {
        "columns": cols,
        "keys": keys,
        "freeze_after": raw.get("freeze_after", "description"),
        "print_through": raw.get("print_through", "status"),
    }
    return layout


def header_map(headers, layout):
    """Map header texts (a list, by position) to column keys.

    Returns ({position: key}, score). Matches the layout header, the layout aliases, the
    built-in aliases and the key itself, ignoring case and punctuation.
    """
    lookup = {}
    for c in layout["columns"]:
        for text in [c["header"], c["key"], *c["aliases"], *BUILTIN_ALIASES.get(c["key"], [])]:
            lookup.setdefault(_norm(text), c["key"])
    found = {}
    for i, h in enumerate(headers):
        k = lookup.get(_norm(h))
        if k and k not in found.values():
            found[i] = k
    return found, len(found)
