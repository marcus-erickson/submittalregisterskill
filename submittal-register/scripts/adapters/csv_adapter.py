"""CSV output and input for the register.

The CSV carries calculated dates as values (Excel and Sheets carry them as formulas), so a
file written here can be imported into another system as is.
"""
import csv

import columns as colmod
import register_model as model


def item_values(item, layout, rules, today=None):
    """One row of display values, in layout order."""
    req_app, req_sub, due = model.compute_dates(item, rules, today)
    review = model.num(item["review"])
    if review is None:
        review = rules.get("review_weeks", model.DEFAULT_RULES["review_weeks"])
    section_title = item["section_title"].title() if item["section_title"].isupper() else item["section_title"]
    by_key = {
        "sub_no": item["sub_no"], "rev": item["rev"], "description": item["description"],
        "section": item["section"], "section_title": section_title, "types": item["types"],
        "ref": item["ref"], "install_date": item["install_date"],
        "lead": "" if model.num(item["lead"]) is None else model.num(item["lead"]),
        "review": review, "prep": rules.get("prep_weeks", model.DEFAULT_RULES["prep_weeks"]),
        "required_approval": req_app, "required_submit": req_sub,
        "actual_submit": item["actual_submit"], "approval_date": item["approval_date"],
        "status": item["status"], "days_to_due": due, "origin": item["origin"],
        "notes": item["notes"] or (item["review_note"] if item["needs_review"] else ""),
        "full": item["full"], "ball_in_court": item["ball_in_court"],
    }
    return [by_key[c["key"]] if c["key"] in by_key else item["extra"].get(c["key"], "")
            for c in layout["columns"]]


def write(register, out, layout):
    rules = register["rules"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([c["header"] for c in layout["columns"]])
        for item in register["items"]:
            w.writerow(item_values(item, layout, rules))
    flagged = sum(1 for i in register["items"] if i["needs_review"])
    return len(register["items"]), flagged


def read_table(headers, body, layout):
    """Shared reader: map a header row and body rows to model items."""
    found, _ = colmod.header_map(headers, layout)
    if not all(k in found.values() for k in colmod.CORE):
        raise ValueError("Could not match a section and a description column. "
                         "Pass a --columns layout whose headers match this file.")
    items = []
    for row in body:
        vals = {key: (row[pos] if pos < len(row) else "") for pos, key in found.items()}
        text = lambda k: str(vals.get(k, "") or "").strip()
        if not text("section") and not text("description"):
            continue
        item = model.blank_item(
            sub_no=text("sub_no"), rev=model.to_int(vals.get("rev")), section=text("section"),
            section_title=text("section_title"), description=text("description"), full=text("full"),
            types=text("types"), ref=text("ref"), origin=text("origin"), notes=text("notes"),
            install_date=model.iso(vals.get("install_date")),
            actual_submit=model.iso(vals.get("actual_submit")),
            approval_date=model.iso(vals.get("approval_date")),
            status=text("status") or "Not Started", ball_in_court=text("ball_in_court"),
        )
        for key in ("lead", "review"):
            n = model.num(vals.get(key))
            item[key] = n if n is not None else ""
        item["extra"] = {k: text(k) for k in vals if k.startswith("x_")}
        items.append(item)
    return items


def read(path, layout):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError("The CSV is empty.")
    return model.new_register("", None, read_table(rows[0], rows[1:], layout))
