#!/usr/bin/env python3
"""The register as plain data, independent of any output format.

A register is a dict:

    {"schema_version": 1,
     "project": "Project name",
     "rules": {review_weeks, prep_weeks, numbering_note, copies_format, rules_source,
               division01_notes, ...},
     "items": [item, ...]}

Every item is a flat dict with these keys:

    sub_no, rev, section, section_title, description, full, types, ref, origin,
    lead, review, notes, needs_review, review_note,
    install_date, actual_submit, approval_date, status, ball_in_court,
    extra  (dict of custom columns, keys that start with x_)

Dates are ISO strings (YYYY-MM-DD) or "". Weeks are numbers or "". Output adapters
(scripts/adapters/) turn this into Excel, CSV, Google Sheets values or JSON, and read it back.
"""
import csv
import math
import json
from collections import defaultdict
from datetime import date, datetime

SCHEMA_VERSION = 1

STATUSES = ["Not Started", "In Prep", "Submitted", "Approved", "Approved as Noted",
            "Revise/Resubmit", "Rejected"]
CLOSED_STATUSES = ("Approved", "Approved as Noted")
TYPE_LEGEND = [
    ("PD", "Product data"), ("SD", "Shop drawings"), ("WD", "Wiring diagrams"),
    ("SAM", "Samples"), ("CALC", "Calculations"), ("CERT", "Certificates, qualifications"),
    ("TEST", "Test and inspection reports"), ("WARR", "Warranties"),
    ("OM", "Operation and maintenance data"), ("MOCKUP", "Mock-ups"),
    ("RECORD", "Record drawings and as-builts"), ("SCHED", "Schedules"),
    ("REPORT", "Surveys, statements, other reports"), ("REF", "Cross-reference to another section"),
    ("OTHER", "Not classified"),
]

DEFAULT_RULES = {"review_weeks": 3, "prep_weeks": 1}


def truthy(v):
    return str(v or "").strip().lower() in ("y", "yes", "true", "1", "x")


def shorten(text, n=240):
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut + "..."


def iso(v):
    """Any date-like value to an ISO string, or ''."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return s


def parse_date(v):
    s = iso(v)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except ValueError:
        return None


def num(v):
    """A number from a cell value, or None. Formulas and text give None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def to_int(v, default=0):
    n = num(v)
    return int(n) if n is not None else default


def blank_item(**kw):
    item = {
        "sub_no": "", "rev": 0, "section": "", "section_title": "", "description": "", "full": "",
        "types": "", "ref": "", "origin": "", "lead": "", "review": "", "notes": "",
        "needs_review": False, "review_note": "", "install_date": "", "actual_submit": "",
        "approval_date": "", "status": "Not Started", "ball_in_court": "", "extra": {},
    }
    item.update(kw)
    return item


def new_register(project="", rules=None, items=None):
    rules = dict(rules or {})
    if project:
        rules["project"] = project
    for k, v in DEFAULT_RULES.items():
        rules.setdefault(k, v)
    return {"schema_version": SCHEMA_VERSION, "project": rules.get("project", ""),
            "rules": rules, "items": items or []}


# ---------------------------------------------------------------- reading the extraction CSV

def load_rows(path, keep_div01=False):
    """Read a draft or reviewed CSV (the format extract.py writes and Claude reviews).

    Optional live columns are read too: rev, install_date, actual_submit, approval_date,
    status, ball_in_court, ref.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    rows = []
    for r in raw:
        full = (r.get("requirement") or r.get("full") or r.get("description") or "").strip()
        desc = (r.get("description") or "").strip() or shorten(full)
        src = r.get("origin") or r.get("source") or ""
        ref = " ".join(x for x in [
            (r.get("article") or "").strip(),
            f"p.{r['page']}" if r.get("page") else ""] if x) or (r.get("ref") or "").strip()
        rows.append(blank_item(
            sub_no=(r.get("sub_no") or "").strip(),
            rev=to_int(r.get("rev")),
            section=(r.get("section") or "").strip(),
            section_title=(r.get("section_title") or "").strip(),
            description=desc,
            full=full,
            types=(r.get("types") or "").strip(),
            ref=ref,
            origin=src,
            lead=(r.get("lead_weeks") or r.get("lead") or "").strip(),
            review=(r.get("review_weeks") or r.get("review") or "").strip(),
            notes=(r.get("notes") or "").strip(),
            needs_review=truthy(r.get("needs_review")) or src.upper().startswith("REVIEW"),
            review_note=(r.get("review_note") or "").strip(),
            install_date=iso(r.get("install_date")),
            actual_submit=iso(r.get("actual_submit")),
            approval_date=iso(r.get("approval_date")),
            status=(r.get("status") or "").strip() or "Not Started",
            ball_in_court=(r.get("ball_in_court") or "").strip(),
        ))
    rows = [r for r in rows if r["section"] and r["description"]]
    if not keep_div01:  # Division 01 procedure text becomes project rules, not register rows
        rows = [r for r in rows if r["origin"].strip().lower() != "division 01 procedure"]
    return rows


def number_rows(rows, scheme):
    counters = defaultdict(int)
    seq = 0
    used = {r["sub_no"] for r in rows if r["sub_no"]}
    for r in rows:
        if r["sub_no"]:
            continue
        if scheme == "compact":  # 061000.01, the section digits then a two-digit sequence
            counters[r["section"]] += 1
            digits = r["section"].replace(" ", "")
            r["sub_no"] = f"{digits}.{counters[r['section']]:02d}"
            continue
        if scheme == "sequential":
            seq += 1
            r["sub_no"] = f"{seq:03d}"
        else:
            counters[r["section"]] += 1
            n = counters[r["section"]]
            cand = f"{r['section']}-{n}"
            while cand in used:
                n += 1
                cand = f"{r['section']}-{n}"
            used.add(cand)
            r["sub_no"] = cand


def load_install(path):
    """Install dates file: section,install_date,lead_weeks (dates as YYYY-MM-DD)."""
    out = {}
    if not path:
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = datetime.strptime(r["install_date"].strip(), "%Y-%m-%d").date() if r.get("install_date") else None
            lead = float(r["lead_weeks"]) if r.get("lead_weeks") else None
            out[r["section"].strip()] = (d, lead)
    return out


def apply_install(rows, install):
    """Fill install date and lead time from the install dates file where the row has none."""
    for r in rows:
        d, lead = install.get(r["section"], (None, None))
        if d and not r["install_date"]:
            r["install_date"] = d.isoformat()
        if r["lead"] in ("", None) and lead is not None:
            r["lead"] = lead


# ---------------------------------------------------------------- derived dates

def compute_dates(item, rules, today=None):
    """Required approval, required submit and days to due, matching the Excel formulas.

    Returns (required_approval, required_submit, days_to_due) as ISO string, ISO string,
    int. Each is "" when it cannot be calculated.
    """
    today = today or date.today()
    inst = parse_date(item.get("install_date"))
    lead = num(item.get("lead"))
    review = num(item.get("review"))
    if review is None:
        review = num(rules.get("review_weeks", DEFAULT_RULES["review_weeks"]))
    prep = num(rules.get("prep_weeks", DEFAULT_RULES["prep_weeks"]))
    if inst is None or lead is None:
        return "", "", ""
    base = inst.toordinal()
    approval = base - 7 * lead
    submit = base - 7 * (lead + (review or 0) + (prep or 0))
    due = ""
    if item.get("status") not in CLOSED_STATUSES:
        due = int(round(submit - today.toordinal()))
    return (date.fromordinal(math.floor(approval)).isoformat(),
            date.fromordinal(math.floor(submit)).isoformat(), due)


# ---------------------------------------------------------------- JSON form

def dump_register(register, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(register, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def load_register(path):
    with open(path, encoding="utf-8") as fh:
        reg = json.load(fh)
    items = []
    for it in reg.get("items", []):
        item = blank_item()
        item.update(it)
        item["extra"] = dict(it.get("extra") or {})
        items.append(item)
    return new_register(reg.get("project", ""), reg.get("rules"), items)
