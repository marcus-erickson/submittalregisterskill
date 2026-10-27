#!/usr/bin/env python3
"""Match submittal documents to register lines and apply status updates to register.json.

Claude reads each uploaded document (a transmittal, a stamped review return, an email saved
as a PDF) and writes events.json. This script does the parts that should be the same every
time: matching an event to a register line with a confidence verdict, checking that the
status change makes sense, writing the update, and keeping an audit log.

Usage:
  intake.py id FILE                      print a stable id for an uploaded file
  intake.py match REGISTER.json EVENTS.json -o MATCHES.json
  intake.py apply REGISTER.json MATCHES.json --log intake-log.csv [--dry-run]

events.json:
  {"events": [{
      "source_id": "3fa9c1d2e07b4a55",  required, from `intake.py id FILE` (stops double-counting)
      "kind": "received" | "returned",  required
      "date": "2026-10-27",             required, the transmittal date or the review stamp date
      "section": "07 21 00",            spec section, if the document gives one
      "title": "Batt insulation",       what the document calls the submittal
      "types": "PD",                    type code if the document says (PD, SD, SAM, ...)
      "sub_no": "07 21 00-1",           the register number, if the document uses one
      "action": "approved" | "approved_as_noted" | "revise_resubmit" | "rejected",  returned only
      "reviewer": "Architect",          received: who the ball goes to
      "submitter": "Contractor",        returned: who the ball goes back to
      "comment": "...",                 optional, appended to Notes
      "source_name": "...",             optional, the file name, kept in the log
      "project_hint": "...",            optional, the project name or number the document shows
      "confirm": false                  true to apply an out-of-order change a person approved
  }]}

received  = a submittal was sent in for review (or arrived for review). Status becomes Submitted.
            A resubmittal after Revise/Resubmit or Rejected raises Rev by one.
returned  = a reviewer's action came back. Status becomes Approved, Approved as Noted,
            Revise/Resubmit or Rejected.

Nothing is guessed. An event that does not match one line with confidence is left for a
person, and a status change that is out of order is reported as a conflict, not applied.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone


def _register_scripts():
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in ("../register-scripts", "../../submittal-register/scripts", "../submittal-register/scripts"):
        p = os.path.normpath(os.path.join(here, rel))
        if os.path.exists(os.path.join(p, "register_model.py")):
            return p
    sys.exit("Cannot find the register scripts. They are bundled in submittal-intake/register-scripts "
             "in the downloaded zip, or in the submittal-register skill installed next to this one.")


sys.path.insert(0, _register_scripts())
import register_model as model  # noqa: E402

ACTIONS = {
    "approved": "Approved", "no_exception_taken": "Approved", "no exceptions taken": "Approved",
    "approved_as_noted": "Approved as Noted", "make_corrections_noted": "Approved as Noted",
    "exceptions_noted": "Approved as Noted",
    "revise_resubmit": "Revise/Resubmit", "revise_and_resubmit": "Revise/Resubmit",
    "resubmit": "Revise/Resubmit",
    "rejected": "Rejected",
}
REOPEN = ("Revise/Resubmit", "Rejected")
STOP = {"the", "and", "for", "with", "from", "per", "all", "shall", "section", "submittal", "submittals",
        "submit", "provide", "required", "requirement", "review"}
LOG_FIELDS = ["applied_at", "result", "key", "source_id", "kind", "sub_no", "section", "from_status",
              "to_status", "rev", "date", "note", "source_name"]


# ------------------------------------------------------------------ matching

def norm_section(s):
    s = str(s or "").strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) == 6:
        return f"{digits[:2]} {digits[2:4]} {digits[4:]}"
    return re.sub(r"\s+", " ", s)


def stem(w):
    """Light plural handling, so sealant and sealants count as the same word."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us")):
        return w[:-1]
    return w


def tokens(text):
    out = set()
    for w in re.findall(r"[a-z0-9]{3,}", str(text or "").lower()):
        st = stem(w)
        if w not in STOP and st not in STOP:
            out.add(st)
    return out


def type_set(text):
    return {t for t in re.split(r"[\s,+/]+", str(text or "").upper()) if t}


def score(event, item):
    """(score, recall, precision). Recall is the share of the document's own words found in the line.

    The score leans on recall: a line that has every word the document uses is a better fit
    than a shorter line that has most of them. Precision (how much of the line the document
    covers) only breaks near ties, so a short line is not favored for being short.
    """
    a, b = tokens(event.get("title")), tokens(item["description"])
    inter = len(a & b)
    recall = inter / len(a) if a else 0.0
    precision = inter / len(b) if b else 0.0
    s = 0.9 * recall + 0.1 * precision
    et = type_set(event.get("types"))
    if et:
        s += 0.1 if et & type_set(item["types"]) else -0.15
    return max(0.0, min(1.0, s)), recall, precision


def candidate(item, s):
    return {"sub_no": item["sub_no"], "score": round(s, 2), "section": item["section"],
            "description": item["description"], "status": item["status"], "rev": item["rev"]}


def wrong_project(hint, rules):
    """True when the project the document names clearly is not this register's project."""
    hint = str(hint or "").strip()
    if not hint:
        return False
    name = f"{rules.get('project', '')} {rules.get('project_number', '')}"
    words = {t for t in tokens(hint) if re.search(r"[a-z]", t)}
    if words:  # compare names to names
        return bool(tokens(name)) and not (words & tokens(name))
    number = re.sub(r"\D", "", hint)  # a bare project number: compare only when the register has one
    have = re.sub(r"\D", "", str(rules.get("project_number", "")))
    return bool(number and have) and number not in have and have not in number


def match_event(event, items, rules=None):
    """Return (candidates, verdict, chosen, reason). Verdict: confident, ambiguous, none or wrong_project."""
    if wrong_project(event.get("project_hint"), rules or {}):
        return ([], "wrong_project", "",
                f"the document names project '{event['project_hint']}', but this register is for "
                f"'{(rules or {}).get('project', '')}'")
    want = str(event.get("sub_no") or "").strip().upper()
    if want:
        hit = [i for i in items if i["sub_no"].strip().upper() == want]
        if hit:
            return [candidate(hit[0], 1.0)], "confident", hit[0]["sub_no"], "register number given in the document"
    section = norm_section(event.get("section"))
    pool = [i for i in items if norm_section(i["section"]) == section] if section else list(items)
    if section and not pool:
        ranked = sorted(((score(event, i)[0], i) for i in items), key=lambda x: -x[0])[:3]
        return ([candidate(i, s) for s, i in ranked if s > 0], "none", "",
                f"section {section} is not in the register")
    ranked = sorted(((*score(event, i), i) for i in pool), key=lambda x: -x[0])
    cands = [candidate(i, s) for s, _, _, i in ranked[:3]]
    if not ranked:
        return [], "none", "", "the register has no lines"
    top, top_overlap, top_prec, top_item = ranked[0]
    gap = top - ranked[1][0] if len(ranked) > 1 else 1.0
    if len(ranked) > 1:
        second = ranked[1]
        # the document quotes one line's wording exactly (at least three meaningful words, so a
        # generic title cannot qualify) and no other line does
        exact = lambda r: r[1] >= 0.99 and r[2] >= 0.99
        if len(tokens(event.get("title"))) >= 3 and exact(ranked[0]) and not exact(second):
            return cands, "confident", top_item["sub_no"], "wording matches one line exactly"
        if top_overlap >= 0.99 and second[1] >= 0.99:
            return cands, "ambiguous", "", "more than one line contains every word the document uses"
        if top_overlap >= 0.99 and second[1] < 0.99 and len(tokens(event.get("title"))) >= 3:
            return cands, "confident", top_item["sub_no"], "only one line contains every word the document uses"
    et = type_set(event.get("types"))
    if section and len(pool) == 1:
        ok = not et or et & type_set(top_item["types"]) or top_overlap >= 0.3
        return (cands, "confident", top_item["sub_no"], "only line in that section") if ok else \
               (cands, "ambiguous", "", "only line in that section, but the type does not match")
    if section and top >= 0.45 and gap >= 0.2:
        return cands, "confident", top_item["sub_no"], "section and title match"
    if not section and top >= 0.6 and gap >= 0.25:
        return cands, "confident", top_item["sub_no"], "title match, no section in the document"
    return cands, "ambiguous", "", "more than one line fits, or the title match is weak"


def cmd_match(a):
    reg = model.load_register(a.register)
    events = json.load(open(a.events, encoding="utf-8"))["events"]
    out = []
    for ev in events:
        cands, verdict, chosen, reason = match_event(ev, reg["items"], reg["rules"])
        out.append({**ev, "candidates": cands, "verdict": verdict, "chosen": chosen, "reason": reason})
    with open(a.o, "w", encoding="utf-8") as fh:
        json.dump({"events": out}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    counts = {v: sum(1 for e in out if e["verdict"] == v) for v in ("confident", "ambiguous", "none", "wrong_project")}
    print(f"{len(out)} events: {counts['confident']} confident, {counts['ambiguous']} ambiguous, {counts['none']} no match, "
          f"{counts['wrong_project']} look like another project")
    for e in out:
        if e["verdict"] != "confident":
            print(f"  needs a person: {e.get('source_name') or e.get('title')} ({e['reason']})")
            for c in e["candidates"]:
                print(f"      {c['sub_no']}  {c['score']}  {c['description'][:70]}")


# ------------------------------------------------------------------ applying

def _append_note(item, text):
    item["notes"] = (item["notes"] + "; " if item["notes"] else "") + text


def apply_event(ev, item):
    """Change the item in place. Returns (result, note) where result is applied or conflict."""
    prev, kind, day = item["status"], ev["kind"], model.iso(ev.get("date"))
    confirm = bool(ev.get("confirm"))
    if not day or not model.parse_date(day):
        return "unresolved", "the event has no usable date"
    if kind == "received":
        if prev in model.CLOSED_STATUSES and not confirm:
            return "conflict", f"already {prev}; a new submission needs a person to confirm"
        if prev == "Submitted" and not confirm:
            return "conflict", "already Submitted with no return logged; confirm if this is a resubmission"
        if prev in REOPEN or (confirm and prev in model.CLOSED_STATUSES):
            item["rev"] = int(item["rev"] or 0) + 1
            item["approval_date"] = ""
        item["status"] = "Submitted"
        item["actual_submit"] = day
        item["ball_in_court"] = ev.get("reviewer") or "Reviewer"
        if ev.get("comment"):
            _append_note(item, f"Sent {day}: {ev['comment']}")
        return "applied", f"{prev} -> Submitted (rev {item['rev']})"
    if kind == "returned":
        action = str(ev.get("action") or "").strip().lower().replace(" ", "_").replace("/", "_")
        status = ACTIONS.get(action) or ACTIONS.get(str(ev.get("action") or "").strip().lower())
        if not status:
            return "unresolved", f"unknown review action '{ev.get('action')}'"
        if prev != "Submitted" and not confirm:
            return "conflict", f"status is {prev}, not Submitted; a return with no submission logged needs a person to confirm"
        item["status"] = status
        closed = status in model.CLOSED_STATUSES
        item["approval_date"] = day if closed else ""
        item["ball_in_court"] = "" if closed else (ev.get("submitter") or "Contractor")
        if ev.get("comment"):
            _append_note(item, f"Returned {day} ({status}): {ev['comment']}")
        return "applied", f"{prev} -> {status}"
    return "unresolved", f"unknown kind '{kind}'"


def read_log(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cmd_apply(a):
    reg = model.load_register(a.register)
    by_no = {i["sub_no"]: i for i in reg["items"]}
    done = {r["key"] for r in read_log(a.log) if r["result"] == "applied"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, tally = [], {}
    events = json.load(open(a.matches, encoding="utf-8"))["events"]
    # oldest first, and a submission before its return on the same day
    events.sort(key=lambda e: (model.iso(e.get("date")), 0 if e.get("kind") == "received" else 1))
    for ev in events:
        sub_no = ev.get("chosen") or ""
        key = f"{ev.get('source_id')}|{sub_no}|{ev.get('kind')}"
        base = {"applied_at": now, "key": key, "source_id": ev.get("source_id", ""), "kind": ev.get("kind", ""),
                "sub_no": sub_no, "section": ev.get("section", ""), "date": ev.get("date", ""),
                "source_name": ev.get("source_name", ""), "from_status": "", "to_status": "", "rev": ""}
        if not ev.get("source_id"):
            result, note = "unresolved", "no source_id, so this could not be kept out of a second run"
        elif not sub_no or sub_no not in by_no:
            result, note = "unresolved", ev.get("reason") or "no register line chosen"
        elif key in done:
            result, note = "skipped", "this document was already applied for that line"
        else:
            item = by_no[sub_no]
            before = item["status"]
            probe = json.loads(json.dumps(item))  # check first, so a conflict changes nothing
            result, note = apply_event(ev, probe)
            if result == "applied":
                item.update(probe)  # kept in memory even on a dry run, so later events in the batch see it
                base.update(from_status=before, to_status=probe["status"], rev=probe["rev"])
        base.update(result=result, note=note)
        rows.append(base)
        tally[result] = tally.get(result, 0) + 1

    if not a.dry_run:
        if tally.get("applied"):
            if os.path.exists(a.register):
                with open(a.register, "rb") as src, open(a.register + ".bak", "wb") as dst:
                    dst.write(src.read())
            tmp = a.register + ".tmp"
            model.dump_register(reg, tmp)
            os.replace(tmp, a.register)
        if a.log and rows:
            new = not os.path.exists(a.log)
            with open(a.log, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
                if new:
                    w.writeheader()
                w.writerows(rows)
    label = "Would apply" if a.dry_run else "Applied"
    print(f"{label} {tally.get('applied', 0)}; skipped {tally.get('skipped', 0)}; "
          f"conflicts {tally.get('conflict', 0)}; unresolved {tally.get('unresolved', 0)}")
    for r in rows:
        if r["result"] != "applied":
            print(f"  {r['result']}: {r['source_name'] or r['source_id']} -> {r['sub_no'] or '?'}: {r['note']}")
    for r in rows:
        if r["result"] == "applied":
            print(f"  {r['sub_no']}: {r['note']}")


def cmd_id(a):
    h = hashlib.sha256()
    with open(a.file, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    print(h.hexdigest()[:16])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("id", help="print a stable id for an uploaded file")
    i.add_argument("file")
    i.set_defaults(fn=cmd_id)
    m = sub.add_parser("match")
    m.add_argument("register")
    m.add_argument("events")
    m.add_argument("-o", required=True)
    m.set_defaults(fn=cmd_match)
    p = sub.add_parser("apply")
    p.add_argument("register")
    p.add_argument("matches")
    p.add_argument("--log", default="intake-log.csv")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_apply)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
