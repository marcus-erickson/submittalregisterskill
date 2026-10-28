#!/usr/bin/env python3
"""Checks for the federal (UFGS) SD-list parser and for section numbers such as `23 31 13.00 40`."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "submittal-register", "scripts"))
import extract as E  # noqa: E402
import specindex as S  # noqa: E402

BODY = """
 Government approval is required for submittals with a "G" or "S"
 classification. Submit the following in accordance with Section 01 33 00 SUBMITTAL
 PROCEDURES:

      SD-01 Preconstruction Submittals

          Quality Control Plan; G

          Quality Control Personnel Certifications; G
          Maturity Method Data

      SD-03 Product Data

          VOC Content for Form Release Agents, Curing Compounds, and
          Concrete Penetrating Sealers

                             SECTION 03 30 00   Page 11

          Safety Data Sheets

      SD-05 Design Data

          Masonry Compressive Strength; GBracing Calculations; G

      SD-06 Test Reports

          Emissions; G
          filters; G
          special tools

1.4   MODIFICATION OF REFERENCES

 Accomplish work in accordance with ACI publications.
"""

items = E.parse_items(BODY)
got = [(i["letter"], i["text"], i["classification"]) for i in items]
want = [
    ("SD-01", "Quality Control Plan", "G"),
    ("SD-01", "Quality Control Personnel Certifications", "G"),
    ("SD-01", "Maturity Method Data", ""),
    ("SD-03", "VOC Content for Form Release Agents, Curing Compounds, and Concrete Penetrating Sealers", ""),
    ("SD-03", "Safety Data Sheets", ""),
    ("SD-05", "Masonry Compressive Strength", "G"),
    ("SD-05", "Bracing Calculations", "G"),
    ("SD-06", "Emissions", "G"),
    ("SD-06", "filters", "G"),
    ("SD-06", "special tools", ""),
]
assert got == want, "\n".join(map(str, got))

# a wrapped "PROCEDURES:" line must not end the article early
text = "1.2   SUBMITTALS\n\n" + BODY
arts = E.submittal_articles(text)
assert any("SD-06" in a[2] for a in arts), "article was cut short"

# federal section numbers keep their two-part suffix
assert S.norm("23 31 13.00 40") == "23 31 13.00 40"
assert S.norm("233113.00 40") == "23 31 13.00 40"
assert S.norm("23 05 48.19") == "23 05 48.19"
print("All checks passed")
