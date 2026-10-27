#!/usr/bin/env python3
"""Generate sample submittal documents for trying the submittal-intake skill.

All companies and people are fictional, every page carries a SAMPLE footer, and the project is
the public bid package used in submittal-register/examples/health-sciences-drainage.

  01  transmittal T-007, contractor to architect, three items, text PDF
  02  review return for T-007, text PDF. All four action boxes are printed; only one has an X,
      so the action can only be read by looking at the page.
  03  stamped cover sheet for one item, image only (no text layer), slightly rotated stamp
  04  transmittal for a different project, to test the wrong-project check

Usage: python3 make_samples.py [output_dir]
"""
import os
import random
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
W, H = letter
PROJECT = "Health Sciences Simulation Lab Drainage Improvements, Northeast Texas Community College"
FOOTER = "SAMPLE DOCUMENT FOR TESTING. Fictional companies and people. Not a real submittal."
CONTRACTOR = ("Lone Star Builders, Inc.", "4120 Industrial Loop, Mount Pleasant, TX")
ARCHITECT = ("Harlan Pierce Architects", "210 Main Street, Texarkana, TX")


def header(c, title, number, date, to, frm, project, project_no):
    c.setFont("Helvetica-Bold", 20)
    c.drawString(54, H - 66, title)
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 54, H - 58, f"{title.title()} No. {number}")
    c.drawRightString(W - 54, H - 72, f"Date: {date}")
    c.line(54, H - 82, W - 54, H - 82)
    y = H - 104
    for label, lines in (("TO:", to), ("FROM:", frm)):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(54, y, label)
        c.setFont("Helvetica", 10)
        for ln in lines:
            c.drawString(104, y, ln)
            y -= 13
        y -= 6
    c.setFont("Helvetica-Bold", 10)
    c.drawString(54, y, "PROJECT:")
    c.setFont("Helvetica", 10)
    c.drawString(104, y, project)
    c.drawString(104, y - 13, f"Project No. {project_no}")
    return y - 38


def footer(c):
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.grey)
    c.drawCentredString(W / 2, 30, FOOTER)
    c.setFillColor(colors.black)


def table(c, y, cols, rows, widths):
    x0 = 54
    c.setFont("Helvetica-Bold", 9)
    x = x0
    c.setFillColor(colors.Color(0.9, 0.9, 0.9))
    c.rect(x0, y - 4, sum(widths), 16, fill=1, stroke=0)
    c.setFillColor(colors.black)
    for name, w in zip(cols, widths):
        c.drawString(x + 3, y, name)
        x += w
    y -= 18
    c.setFont("Helvetica", 9)
    for row in rows:
        x = x0
        for cell, w in zip(row, widths):
            c.drawString(x + 3, y, cell)
            x += w
        c.line(x0, y - 5, x0 + sum(widths), y - 5)
        y -= 20
    return y


def doc_transmittal(path, number, date, project, project_no, rows, remarks):
    c = canvas.Canvas(path, pagesize=letter)
    y = header(c, "TRANSMITTAL", number, date, [ARCHITECT[0], ARCHITECT[1], "Attn: Review of submittals"],
               [CONTRACTOR[0], CONTRACTOR[1], "Project Manager: D. Whitfield"], project, project_no)
    y = table(c, y, ["Item", "Spec Section", "Description", "Type", "Copies", "Action"],
              rows, [34, 78, 250, 44, 42, 64])
    c.setFont("Helvetica-Bold", 10)
    c.drawString(54, y - 16, "Remarks:")
    c.setFont("Helvetica", 10)
    for n, ln in enumerate(remarks):
        c.drawString(54, y - 32 - n * 13, ln)
    c.drawString(54, 110, "Sent by: Email and hard copy      Signed: D. Whitfield")
    footer(c)
    c.save()


def doc_review_return(path):
    c = canvas.Canvas(path, pagesize=letter)
    y = header(c, "SUBMITTAL REVIEW", "R-007", "October 19, 2026",
               [CONTRACTOR[0], CONTRACTOR[1], "Attn: D. Whitfield"],
               [ARCHITECT[0], ARCHITECT[1], "Reviewer: M. Okafor, AIA"], PROJECT, "2025-114")
    c.setFont("Helvetica", 10)
    c.drawString(54, y, "Re: your Transmittal T-007 dated 10/05/2026. Review actions are marked below.")
    y -= 26
    actions = ["No Exceptions Taken", "Make Corrections Noted", "Revise and Resubmit", "Rejected"]
    items = [
        ("1", "31 20 00", "Material test reports", 1, "Provide lab accreditation certificate with the next report."),
        ("2", "03 30 53", "Concrete design mixtures", 2, "Mix design for the 4000 psi slab lacks admixture data sheets. Resubmit."),
    ]
    for no, sec, desc, chosen, note in items:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(54, y, f"Item {no}   Spec Section {sec}   {desc}")
        y -= 20
        x = 70
        for k, label in enumerate(actions):
            c.rect(x, y - 2, 9, 9)
            if k == chosen:
                c.setLineWidth(1.6)
                c.line(x, y - 2, x + 9, y + 7)
                c.line(x, y + 7, x + 9, y - 2)
                c.setLineWidth(1)
            c.setFont("Helvetica", 8.5)
            c.drawString(x + 13, y, label)
            x += 125
        y -= 18
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(70, y, f"Comment: {note}")
        y -= 34
    c.setFont("Helvetica", 9)
    c.drawString(54, y, "Item 3 (joint sealants) is still under review and will be returned separately.")
    c.drawString(54, 110, "Reviewed by: M. Okafor, AIA      Date: 10/19/2026")
    footer(c)
    c.save()


def font(size, bold=False):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def doc_scanned_stamp(path):
    random.seed(7)
    img = Image.new("L", (1275, 1650), 250)  # 150 dpi letter page
    d = ImageDraw.Draw(img)
    d.text((90, 90), "SUBMITTAL COVER SHEET", font=font(44, True), fill=20)
    name_lines = textwrap.wrap(PROJECT, 44)
    rows = [("Project:" if i == 0 else "", ln) for i, ln in enumerate(name_lines)] + [("Contractor:", CONTRACTOR[0]),
            ("Submittal No.:", "047"), ("Spec Section:", "32 13 73"),
            ("Description:", "Paving Joint Sealants - Product Data"), ("", "Cold-applied, Type NS, color: gray"),
            ("Date sent:", "10/05/2026")]
    y = 210
    for label, val in rows:
        d.text((90, y), label, font=font(28, True), fill=30)
        d.text((380, y), val, font=font(28), fill=30)
        y += 52
    # review stamp, rotated and slightly uneven like a real ink stamp
    stamp = Image.new("L", (640, 330), 255)
    sd = ImageDraw.Draw(stamp)
    sd.rectangle((8, 8, 632, 322), outline=70, width=6)
    sd.text((40, 30), "HARLAN PIERCE ARCHITECTS", font=font(32, True), fill=70)
    sd.text((40, 90), "[X] NO EXCEPTIONS TAKEN", font=font(34, True), fill=60)
    sd.text((40, 150), "[ ] MAKE CORRECTIONS NOTED", font=font(26), fill=110)
    sd.text((40, 190), "[ ] REVISE AND RESUBMIT   [ ] REJECTED", font=font(24), fill=110)
    sd.text((40, 250), "Date: 10/22/2026    By: M.O.", font=font(30, True), fill=60)
    stamp = stamp.rotate(4, expand=True, fillcolor=255, resample=Image.BICUBIC)
    mask = stamp.point(lambda v: 255 - v)
    img.paste(stamp, (560, 760), mask)
    d.text((90, 1580), FOOTER, font=font(20), fill=140)
    # scan look: skew, blur, speckle
    img = img.rotate(-0.6, expand=False, fillcolor=250, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.9))
    px = img.load()
    for _ in range(9000):
        x, yy = random.randrange(img.width), random.randrange(img.height)
        px[x, yy] = max(0, px[x, yy] - random.randrange(30, 120))
    tmp = path + ".png"
    img.save(tmp)
    c = canvas.Canvas(path, pagesize=letter)
    c.drawImage(ImageReader(tmp), 0, 0, W, H)
    c.save()
    os.remove(tmp)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    doc_transmittal(os.path.join(OUT, "01-transmittal-T-007.pdf"), "T-007", "10/05/2026", PROJECT, "2025-114", [
        ("1", "31 20 00", "Material test reports", "TEST", "2", "Review"),
        ("2", "03 30 53", "Concrete design mixtures", "TEST", "2", "Review"),
        ("3", "32 13 73", "Joint sealants - product data and color chart", "PD", "2", "Review"),
    ], ["Please review and return. Hard copies follow by courier.", "Color selection for sealants is requested with this review."])
    doc_review_return(os.path.join(OUT, "02-review-return-R-007.pdf"))
    doc_scanned_stamp(os.path.join(OUT, "03-stamped-cover-sheet-scanned.pdf"))
    doc_transmittal(os.path.join(OUT, "04-transmittal-other-project.pdf"), "T-112", "10/12/2026",
                    "Westside Elementary School Renovation, Texarkana ISD", "2026-031", [
        ("1", "07 21 00", "Batt insulation - product data", "PD", "2", "Review"),
    ], ["Submitted for review. Please return with the stamped copy."])
    print("Wrote 4 sample documents to", OUT)
