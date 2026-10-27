#!/usr/bin/env python3
"""Measure how well the intake matcher finds a register line from noisy wording.

For every line in the example registers, build events from that line's own description (full,
first five words, without the first word, and with plurals flipped), give the right section
and type, and see what the matcher does. The ground truth is the line the event came from.

  wrong confident  the matcher was sure and wrong. This is the number to keep at zero.
  asked            ambiguous, so a person is asked. Some of this is correct: two lines in one
                   section can read the same.
  right confident  sure and right.

Run from the repository root:  python3 tests/eval_matching.py
"""
import importlib.util
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
spec = importlib.util.spec_from_file_location("intake", os.path.join(ROOT, "submittal-intake", "scripts", "intake.py"))
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)
model = intake.model

EX = os.path.join(ROOT, "submittal-register", "examples")


def flip(word):
    w = word.lower()
    return w[:-1] if w.endswith("s") and len(w) > 3 else w + "s"


def variants(desc):
    words = desc.replace(",", " ").replace(":", " ").split()
    return {
        "full": " ".join(words[:18]),
        "first5": " ".join(words[:5]),
        "drop1": " ".join(words[1:8]),
        "plural": " ".join(flip(w) for w in words[:8]),
    }


def evaluate(name):
    rows = model.load_rows(os.path.join(EX, f"{name}-reviewed.csv"))
    model.number_rows(rows, "section")
    totals = {}
    wrong = []
    for item in rows:
        for kind, title in variants(item["description"]).items():
            ev = {"section": item["section"], "title": title, "types": item["types"].split("+")[0]}
            _, verdict, chosen, _ = intake.match_event(ev, rows, {})
            t = totals.setdefault(kind, {"right": 0, "wrong": 0, "asked": 0, "n": 0})
            t["n"] += 1
            if verdict == "confident":
                if chosen == item["sub_no"]:
                    t["right"] += 1
                else:
                    t["wrong"] += 1
                    wrong.append((item["sub_no"], chosen, kind, title[:50]))
            else:
                t["asked"] += 1
    return totals, wrong, len(rows)


def main():
    show = "--wrong" in sys.argv
    all_wrong = 0
    for name in ("health-sciences-drainage", "radiology-volb"):
        totals, wrong, n = evaluate(name)
        print(f"{name}: {n} lines")
        for kind, t in totals.items():
            print(f"   {kind:7} right confident {t['right']:4}  wrong confident {t['wrong']:3}  asked {t['asked']:4}   of {t['n']}")
        all_wrong += len(wrong)
        if show:
            for w in wrong[:15]:
                print("      WRONG", w)
    print(f"\nwrong confident, all variants: {all_wrong}")


if __name__ == "__main__":
    main()
