#!/usr/bin/env python3
"""Compare two submittal registers for the same project and report what changed in substance.

The point is the meaningful differences: submittals added, deleted, moved to another spec
section, and changed in type or approval requirement. Rewording, plurals, punctuation, numbering
and row order are ignored (they are counted, not listed). Claude reviews the few pairs the script
cannot settle and writes the summary.

Usage:
  compare_registers.py OLD NEW [-o result.json] [--xlsx report.xlsx]
                       [--old-label NAME] [--new-label NAME]
                       [--resolve resolutions.json] [--min-match 0.5]

OLD and NEW can be a register .xlsx, .csv or .json, or a reviewed/draft CSV from extract.py.

resolutions.json settles pairs listed under "to_confirm" in a previous result:
  {"pairs": [{"old": "O12", "new": "N30", "same": true}, {"old": "O7", "new": "N9", "same": false}]}
"""
import argparse
import collections
import json
import os
import re
import sys


def _register_scripts():
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in ("../register-scripts", "../../submittal-register/scripts", "../submittal-register/scripts"):
        p = os.path.normpath(os.path.join(here, rel))
        if os.path.exists(os.path.join(p, "register_io.py")):
            return p
    sys.exit("Cannot find the register scripts. They are bundled in submittal-compare/register-scripts "
             "in the downloaded zip, or in the submittal-register skill installed next to this one.")


sys.path.insert(0, _register_scripts())
import columns as colmod  # noqa: E402
import register_io  # noqa: E402

STOP = {"the", "and", "for", "with", "from", "per", "of", "a", "an", "to", "in", "on", "or", "at", "by", "as",
        "all", "each", "any", "including", "submit", "provide", "required", "requirement"}
ABBREV = {"cert": "certificate", "certs": "certificate", "mfr": "manufacturer", "mfg": "manufacturer",
          "calc": "calculation", "calcs": "calculation", "o&m": "om"}


def stem(w):
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokens(text):
    text = re.sub(r";\s*[GS]\b.*$", "", text or "")  # approval marking is compared separately
    text = text.lower().replace("&", " and ").replace("/", " ").replace("-", " ")
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u2013", " ").replace("\u2014", " ")
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9.\-']*", text):
        w = ABBREV.get(w, w).strip(".-'")
        if not w or w in STOP:
            continue
        out.append(stem(w))
    return out


def norm_key(text):
    return " ".join(sorted(set(tokens(text))))


def similarity(a, b):
    """0 to 1. Same words in any order and form = 1. Containment counts, so a longer description
    that still names the same thing scores high."""
    A, B = set(a), set(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    if inter == 0:
        return 0.0
    jac = inter / len(A | B)
    cont = inter / min(len(A), len(B)) if min(len(A), len(B)) >= 2 else jac
    return 0.5 * jac + 0.5 * cont


def type_set(t):
    """Type codes as a set. OTHER and REF mean 'not classified', so they count as no type."""
    return frozenset(x for x in re.split(r"[+/, ]+", (t or "").upper()) if x and x not in ("OTHER", "REF"))


def approval(item):
    """G (Government/approval), S (sustainability) or '' from the notes or the description."""
    blob = f"{item.get('notes', '')} {item.get('description', '')}"
    m = re.search(r"classification\s+([GS])\b", blob, re.I) or re.search(r";\s*([GS])\b", blob)
    return m.group(1).upper() if m else ""


def short(item, n=90):
    d = " ".join((item.get("description") or "").split())
    return d if len(d) <= n else d[:n].rsplit(" ", 1)[0] + "..."


def load(path, label):
    reg = register_io.load_input(path, colmod.load(None))
    items = []
    for i, it in enumerate(reg["items"], 1):
        it = dict(it)
        it["id"] = f"{label}{i}"
        it["toks"] = tokens(it.get("description", ""))
        it["key"] = norm_key(it.get("description", ""))
        it["sec"] = re.sub(r"\s+", " ", (it.get("section") or "").strip())
        it["tset"] = type_set(it.get("types"))
        it["appr"] = approval(it)
        items.append(it)
    return reg, items


TRACK_FIELDS = [("status", "Status"), ("rev", "Rev"), ("actual_submit", "Submitted"), ("approval_date", "Approved"),
                ("lead", "Lead weeks"), ("review", "Review weeks"), ("ball_in_court", "Ball in court")]


def tracking_changes(o, n):
    out = []
    for f, name in TRACK_FIELDS:
        a, b = o.get(f), n.get(f)
        a = "" if a in (None, 0, "0", "Not Started") and f in ("rev", "status") else a
        b = "" if b in (None, 0, "0", "Not Started") and f in ("rev", "status") else b
        if str(a or "").strip() != str(b or "").strip():
            out.append((name, a or "", b or ""))
    return out


def match(old, new, min_match, resolutions):
    """One-to-one matching. Same section first, then leftovers across sections."""
    pairs, used_o, used_n = [], set(), set()
    forced_same = {(r["old"], r["new"]) for r in resolutions if r.get("same")}
    forced_diff = {(r["old"], r["new"]) for r in resolutions if not r.get("same")}
    byid_o = {o["id"]: o for o in old}
    byid_n = {n["id"]: n for n in new}
    for a, b in forced_same:
        if a in byid_o and b in byid_n and a not in used_o and b not in used_n:
            pairs.append((byid_o[a], byid_n[b], 1.0, "confirmed"))
            used_o.add(a); used_n.add(b)

    def cand(o_list, n_list, floor, same_section):
        c = []
        for o in o_list:
            for n in n_list:
                if o["id"] in used_o or n["id"] in used_n or (o["id"], n["id"]) in forced_diff:
                    continue
                if same_section and o["sec"] != n["sec"]:
                    continue
                s = 1.0 if o["key"] and o["key"] == n["key"] else similarity(o["toks"], n["toks"])
                if s < floor:
                    continue
                if o["tset"] and o["tset"] == n["tset"]:
                    s += 0.04  # same type breaks ties between look-alike lines
                c.append((s, o, n))
        c.sort(key=lambda x: (-x[0], x[1]["id"]))
        return c

    for floor, same_section, how in ((min_match, True, "same section"), (0.85, False, "moved")):
        for s, o, n in cand(old, new, floor, same_section):
            if o["id"] in used_o or n["id"] in used_n:
                continue
            pairs.append((o, n, min(s, 1.0), how))
            used_o.add(o["id"]); used_n.add(n["id"])
    return pairs, [o for o in old if o["id"] not in used_o], [n for n in new if n["id"] not in used_n]


REWORD_OK = 0.80      # at or above: same item, wording differs a little (ignored, counted)
CONFIRM_BELOW = 0.65  # a pair in the middle band is shown for Claude to confirm


def _elaboration(o, n):
    """One description is the other plus a few more words (`Fabrication Drawings` and
    `Fabrication Drawings Including Details of Connections`). Same submittal, more detail."""
    A, B = set(o["toks"]), set(n["toks"])
    small, big = (A, B) if len(A) <= len(B) else (B, A)
    has_id = any(re.search(r"\d", t) for t in small)  # `Item A5135` elaborated into its full name
    return len(small) >= 1 and small <= big and (len(big - small) <= 8 or has_id)


def compare(old, new, min_match=0.5, resolutions=()):
    pairs, deleted, added = match(old, new, min_match, resolutions)
    res = {"added": [], "deleted": [], "modified": [], "moved": [], "tracking": [], "minor": [], "to_confirm": []}
    for o, n, s, how in pairs:
        reasons = []
        if o["tset"] and n["tset"] and o["tset"] != n["tset"]:
            reasons.append(("type", "/".join(sorted(o["tset"])) or "(none)", "/".join(sorted(n["tset"])) or "(none)"))
        if o["appr"] != n["appr"]:
            reasons.append(("approval", o["appr"] or "none", n["appr"] or "none"))
        if how == "confirmed" or o["key"] == n["key"]:
            wording = "same"
        elif s >= REWORD_OK or _elaboration(o, n):
            wording = "minor"
        else:
            wording = "changed"
        if wording == "changed":
            reasons.append(("wording", short(o), short(n)))
        rec = {"old_id": o["id"], "new_id": n["id"], "section_old": o["sec"], "section_new": n["sec"],
               "old": short(o), "new": short(n), "types_old": o.get("types", ""), "types_new": n.get("types", ""),
               "score": round(s, 2)}
        if how == "moved" or o["sec"] != n["sec"]:
            res["moved"].append(rec)
        if reasons:
            rec["changes"] = [{"what": w, "from": a, "to": b} for w, a, b in reasons]
            res["modified"].append(rec)
        elif wording == "minor":
            res["minor"].append(rec)
        tc = tracking_changes(o, n)
        if tc:
            res["tracking"].append(dict(rec, tracking=[{"field": f, "from": a, "to": b} for f, a, b in tc]))
        if how == "same section" and wording == "changed" and s < CONFIRM_BELOW:
            res["to_confirm"].append(dict(rec, why="Wording changed a lot. Same submittal reworded, or a different one?"))
    for n in added:
        res["added"].append({"id": n["id"], "section": n["sec"], "description": short(n, 140), "types": n.get("types", ""), "approval": n["appr"], "unconfirmed": bool(n.get("needs_review"))})
    for o in deleted:
        res["deleted"].append({"id": o["id"], "section": o["sec"], "description": short(o, 140), "types": o.get("types", ""), "approval": o["appr"], "unconfirmed": bool(o.get("needs_review"))})
    # possible renames: an unmatched old and new item in the same section that share some words
    seen = set()
    for o in deleted:
        best = None
        for n in added:
            if n["sec"] != o["sec"] or n["id"] in seen:
                continue
            s = similarity(o["toks"], n["toks"])
            if s >= 0.35 and (best is None or s > best[0]):
                best = (s, n)
        if best:
            seen.add(best[1]["id"])
            res["to_confirm"].append({"old_id": o["id"], "new_id": best[1]["id"], "section_old": o["sec"], "section_new": best[1]["sec"],
                                      "old": short(o), "new": short(best[1]), "score": round(best[0], 2),
                                      "why": "Deleted here and added there with some words in common. A rename, or two different submittals?"})
    return res


def roll_up(old, new, res):
    """Section-level picture: what changed and where, so the summary can lead with the big moves."""
    o_by, n_by = collections.Counter(i["sec"] for i in old), collections.Counter(i["sec"] for i in new)
    add_by = collections.Counter(a["section"] for a in res["added"])
    del_by = collections.Counter(d["section"] for d in res["deleted"])
    mod_by = collections.Counter(m["section_new"] for m in res["modified"])
    title = {}
    for i in old + new:
        if i.get("section_title") and not title.get(i["sec"]):
            title[i["sec"]] = i["section_title"]
    rows = []
    for sec in sorted(set(o_by) | set(n_by)):
        a, d, m = add_by[sec], del_by[sec], mod_by[sec]
        base = max(o_by[sec], n_by[sec])
        rows.append({"section": sec, "title": title.get(sec, ""), "old_count": o_by[sec], "new_count": n_by[sec],
                     "added": a, "deleted": d, "modified": m,
                     "status": ("new section" if o_by[sec] == 0 else "section removed" if n_by[sec] == 0 else
                                "heavily changed" if base >= 3 and (a + d + m) / base >= 0.5 else
                                "changed" if (a + d + m) else "unchanged")})
    themes = []
    for r in rows:
        if r["status"] == "new section" and r["new_count"] >= 3:
            themes.append(f"Section {r['section']} {r['title']} is new: {r['new_count']} submittals.")
        elif r["status"] == "section removed" and r["old_count"] >= 3:
            themes.append(f"Section {r['section']} {r['title']} was removed: {r['old_count']} submittals.")
    for kind in ("type", "approval"):
        ctr = collections.Counter((c["from"], c["to"]) for m in res["modified"] for c in m.get("changes", []) if c["what"] == kind)
        for (a, b), k in ctr.most_common(3):
            if k >= 3:
                themes.append(f"{k} submittals changed {kind} from {a} to {b}.")
    for r in sorted((r for r in rows if r["status"] == "heavily changed"), key=lambda r: -(r["added"] + r["deleted"] + r["modified"]))[:5]:
        themes.append(f"Section {r['section']} {r['title']} changed a lot: +{r['added']} added, -{r['deleted']} deleted, {r['modified']} modified (of {max(r['old_count'], r['new_count'])}).")
    mv = collections.Counter((m["section_old"], m["section_new"]) for m in res["moved"])
    for (a, b), k in mv.most_common(3):
        if a != b:
            themes.append(f"{k} submittals moved from section {a} to {b}.")
    return rows, themes


def write_xlsx(path, out):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    hdr = PatternFill("solid", fgColor="1B3A4B")

    def sheet(name, cols, rows, widths):
        ws = wb.create_sheet(name)
        ws.append(cols)
        for c in ws[1]:
            c.fill, c.font = hdr, Font(bold=True, color="FFFFFF")
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        if rows:
            ws.auto_filter.ref = ws.dimensions

    ws = wb.active
    ws.title = "Summary"
    ws.append(["Old register", out["old_label"], f"{out['counts']['old']} submittals"])
    ws.append(["New register", out["new_label"], f"{out['counts']['new']} submittals"])
    ws.append([])
    for k in ("added", "deleted", "modified", "moved", "tracking", "minor", "to_confirm"):
        nice = {"minor": "Wording differences ignored", "tracking": "Tracking changes (status, dates)", "to_confirm": "Pairs to confirm"}.get(k, k.capitalize())
        ws.append([nice, len(out[k])])
    ws.append([])
    ws.append(["What changed in substance"])
    for t in out["themes"]:
        ws.append([t])
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 20
    for r in ws.iter_rows(min_row=1, max_row=10):
        if r[0].value:
            r[0].font = Font(bold=True)
    ws.cell(row=ws.max_row - len(out["themes"]), column=1).font = Font(bold=True)
    sheet("By section", ["Section", "Title", "Old", "New", "Added", "Deleted", "Modified", "Status"],
          [[r["section"], r["title"], r["old_count"], r["new_count"], r["added"], r["deleted"], r["modified"], r["status"]] for r in out["sections"]],
          [16, 44, 7, 7, 8, 9, 9, 18])
    sheet("Added", ["Section", "Submittal", "Types", "Approval", "Still flagged for review"], [[a["section"], a["description"], a["types"], a["approval"], "yes" if a["unconfirmed"] else ""] for a in out["added"]], [16, 100, 12, 10, 12])
    sheet("Deleted", ["Section", "Submittal", "Types", "Approval", "Still flagged for review"], [[a["section"], a["description"], a["types"], a["approval"], "yes" if a["unconfirmed"] else ""] for a in out["deleted"]], [16, 100, 12, 10, 12])
    sheet("Modified", ["Section", "Submittal (old)", "Submittal (new)", "What changed", "From", "To"],
          [[m["section_new"], m["old"], m["new"], c["what"], c["from"], c["to"]] for m in out["modified"] for c in m["changes"]], [16, 60, 60, 12, 40, 40])
    sheet("Moved", ["From section", "To section", "Submittal"], [[m["section_old"], m["section_new"], m["new"]] for m in out["moved"]], [14, 14, 100])
    sheet("Tracking", ["Section", "Submittal", "Field", "From", "To"],
          [[m["section_new"], m["new"], t["field"], t["from"], t["to"]] for m in out["tracking"] for t in m["tracking"]], [16, 80, 16, 20, 20])
    sheet("To confirm", ["Old id", "New id", "Section", "Old", "New", "Similarity", "Question"],
          [[m["old_id"], m["new_id"], m["section_new"], m["old"], m["new"], m["score"], m["why"]] for m in out["to_confirm"]], [8, 8, 14, 60, 60, 10, 60])
    sheet("Wording only", ["Section", "Old", "New", "Similarity"], [[m["section_new"], m["old"], m["new"], m["score"]] for m in out["minor"]], [16, 70, 70, 10])
    wb.save(path)


def digest(out):
    c = out["counts"]
    lines = [f"Old: {out['old_label']} ({c['old']} submittals)   New: {out['new_label']} ({c['new']} submittals)",
             f"Added {len(out['added'])}, deleted {len(out['deleted'])}, modified {len(out['modified'])}, moved {len(out['moved'])}; "
             f"{len(out['minor'])} wording-only differences ignored; {len(out['tracking'])} with tracking changes; "
             f"{len(out['to_confirm'])} pairs to confirm."]
    unc = sum(1 for x in out["added"] + out["deleted"] if x.get("unconfirmed"))
    if unc:
        lines.append(f"{unc} of the added and deleted rows are still flagged for review in their register, so treat them as unconfirmed.")
    if out["themes"]:
        lines.append("")
        lines.append("What changed in substance:")
        lines += [f"  - {t}" for t in out["themes"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("-o", "--out")
    ap.add_argument("--xlsx")
    ap.add_argument("--old-label")
    ap.add_argument("--new-label")
    ap.add_argument("--resolve")
    ap.add_argument("--min-match", type=float, default=0.5)
    a = ap.parse_args()
    try:
        _, old = load(a.old, "O")
        _, new = load(a.new, "N")
    except ValueError as e:
        sys.exit(str(e))
    if not old or not new:
        sys.exit("One of the registers has no rows.")
    res_in = []
    if a.resolve:
        with open(a.resolve, encoding="utf-8") as fh:
            res_in = json.load(fh).get("pairs", [])
    res = compare(old, new, a.min_match, res_in)
    sections, themes = roll_up(old, new, res)
    out = dict(res, sections=sections, themes=themes, counts={"old": len(old), "new": len(new)},
               old_label=a.old_label or os.path.basename(a.old), new_label=a.new_label or os.path.basename(a.new))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
    if a.xlsx:
        write_xlsx(a.xlsx, out)
    print(digest(out))


if __name__ == "__main__":
    main()
