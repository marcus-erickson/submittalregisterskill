"""Section indexer for CSI-format project manuals.

Builds a section list from the manual's own table of contents, then locates
each section's page range in the extracted text.
"""
import re
import subprocess
from dataclasses import dataclass

NUM = r"(?:\d{2}\s?\d{2}\s?\d{2}(?:\.\d+(?: \d{2}(?!\d))?)?|\d{5})(?!\d)"  # federal numbers can end ".00 40"
TOC_LINE = re.compile(rf"^\s*(?:Section\s+)?({NUM})\s*[-–—]?\s*([A-Za-z].*?)\s*$", re.I)
PAGEREF = re.compile(r"(?:\s*\.{3,}.*|\s{2,}[\w.]+(?:\s*[-–]\s*[\w.]+)?)\s*$")


@dataclass
class Section:
    number: str
    title: str
    start_page: int = 0
    end_page: int = 0
    found: bool = False
    toc_number: str = ""  # number the table of contents gave, when the body header differs


def norm(num: str) -> str:
    head, _, suffix = num.strip().partition(".")
    base = re.sub(r"\s", "", head)
    suffix = re.sub(r"\s+", " ", suffix.strip())
    if len(base) == 5:
        out = base
    else:
        out = f"{base[0:2]} {base[2:4]} {base[4:6]}"
    return out + (f".{suffix}" if suffix else "")


def to_pdf(path: str) -> str:
    """Word files are converted to PDF with LibreOffice so page numbers exist; PDFs pass through."""
    import os, tempfile
    if not path.lower().endswith((".docx", ".doc", ".rtf", ".odt")):
        return path
    out = tempfile.mkdtemp(prefix="specconv_")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", out, path],
                   capture_output=True, check=True)
    return os.path.join(out, os.path.splitext(os.path.basename(path))[0] + ".pdf")


def load_pages(pdf_path: str) -> list[str]:
    pdf_path = to_pdf(pdf_path)
    text = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, errors="ignore", check=True,
    ).stdout
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def parse_toc(pages: list[str], toc_first=1, toc_last=60):
    """Read section number and title pairs from the table of contents.

    Returns (sections, last_toc_page). The TOC starts at the first page headed
    TABLE OF CONTENTS and ends after two consecutive pages with no entries.
    """
    sections, seen = [], set()
    in_toc, last_hit, misses = False, 0, 0
    for i in range(toc_first - 1, min(toc_last, len(pages))):
        if not in_toc and "TABLE OF CONTENTS" in pages[i][:500].upper():
            in_toc = True
        if not in_toc:
            continue
        if re.search(r"^\s*PART\s+1\b", pages[i], re.M | re.I):
            break  # specification body has started; its SECTION header is not a table of contents line
        first = next((l for l in pages[i].split("\n") if l.strip()), "")
        if re.match(r"^\s*SECTION\s+" + NUM, first) and sum(bool(TOC_LINE.match(l)) for l in pages[i].split("\n")) <= 1:
            break  # a page that opens with a SECTION header and has no list of entries is body text
        got = 0
        for line in pages[i].split("\n"):
            m = TOC_LINE.match(line)
            if not m:
                continue
            title = PAGEREF.sub("", m.group(2)).strip()
            title = re.sub(r"(?:\s+\d{5,6}\.\d+)+$", "", title)
            if len(title) < 3 or re.search(r",\s*(?:Ste|Suite)\b", title, re.I):
                continue  # too short, or a street address such as "10001 Reunion Place, Ste. 200"
            n = norm(m.group(1))
            got += 1
            if n not in seen:
                seen.add(n)
                sections.append(Section(n, title))
        if got:
            last_hit, misses = i + 1, 0
        else:
            misses += 1
            if misses >= 2 and sections:
                break
    return sections, last_hit


def locate(sections: list[Section], pages: list[str], skip_before=1) -> None:
    """Find each section's start page.

    Sections appear in the manual in table-of-contents order, so each start
    page must come after the previous section's start. A hit is a
    `SECTION nn nn nn` line near the top of a page (strong), a running footer
    such as `23 73 13 - 2` (weaker), or the section title near the top of a
    page (fallback for typos in the table of contents).
    """
    head = re.compile(rf"^\s*SECTION\s+({NUM})", re.I | re.M)
    foot = re.compile(rf"^\s*({NUM})\s*[-\u2013]\s*\d+\s*$", re.M)
    foot_inline = re.compile(rf"({NUM})\s*[-\u2013]\s*\d+\s*$", re.M)
    foot_dot = re.compile(r"(?<!\d)(\d{5,6})\.\d+\s*$", re.M)
    strong: dict[str, list[int]] = {}
    weak: dict[str, list[int]] = {}
    for i, p in enumerate(pages, start=1):
        if i <= skip_before:
            continue
        for m in head.finditer(p[:700]):
            strong.setdefault(norm(m.group(1)), []).append(i)
        tail = p[-300:]
        for rx in (foot, foot_inline, foot_dot):
            for m in rx.finditer(tail):
                weak.setdefault(norm(m.group(1)), []).append(i)

    def tnorm(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())

    # pass 1: header and footer hits only, enforcing table-of-contents order
    prev = skip_before
    for s in sections:
        cands = [h for h in strong.get(s.number, []) if h > prev]
        if not cands:
            cands = [h for h in weak.get(s.number, []) if h > prev]
        if cands:
            s.start_page, s.found = min(cands), True
            prev = s.start_page

    # pass 2: title match, limited to the window between located neighbours
    for idx, s in enumerate(sections):
        if s.found:
            continue
        lo = max((x.start_page for x in sections[:idx] if x.found), default=skip_before)
        hi = min((x.start_page for x in sections[idx + 1:] if x.found), default=len(pages) + 1)
        want = tnorm(s.title)[:25]
        if not want:
            continue
        for i in range(lo + 1, hi):
            if want in tnorm(pages[i - 1][:700]):
                s.start_page, s.found = i, True
                break


def discover_unlisted(sections, pages, skip_before):
    """Add sections that have a body header but no (matching) table of contents entry.

    Real manuals often disagree with their own TOC: a section is missing, or its
    number differs (TOC says 02 41 00, the body says SECTION 024119). Each body
    header whose number is not in the TOC becomes a section of its own. A TOC
    entry that was matched only by title to the same page is replaced.
    """
    head = re.compile(rf"^\s*SECTION\s+({NUM})\s*(?:[-\u2013]\s*(.*))?$", re.I | re.M)
    known = {s.number for s in sections}
    starts = {s.start_page for s in sections if s.found}
    added = []
    for i, p in enumerate(pages, start=1):
        if i <= skip_before:
            continue
        m = head.search(p[:700])
        if not m:
            continue
        n = norm(m.group(1))
        if n in known:
            continue
        title = (m.group(2) or "").strip()
        if not title:  # title is on the next non-empty line
            rest = p[m.end():m.end() + 300].split("\n")
            title = next((x.strip() for x in rest if x.strip()), "")
        if title.upper().startswith("PART") or re.search(r"[a-z]", title) and not title.isupper():
            title = ""  # real section titles are in capitals; anything else is body text
        known.add(n)
        added.append(Section(n, title.title() if title.isupper() else title, start_page=i, found=True))
    if not added:
        return []
    # a TOC entry matched by title to the page of a discovered section is superseded by it
    page_of_new = {a.start_page for a in added}
    old_title = {s.start_page: s.title for s in sections if s.found and s.start_page in page_of_new}
    old_num = {s.start_page: s.number for s in sections if s.found and s.start_page in page_of_new}
    for a in added:
        if not a.title:
            a.title = old_title.get(a.start_page, "")
        a.toc_number = old_num.get(a.start_page, "")
    sections[:] = [s for s in sections if not (s.found and s.start_page in page_of_new)]
    sections.extend(added)
    sections.sort(key=lambda s: (s.start_page if s.found else 10**9))
    return added


def single_item_spec(pages):
    """Fallback for files with no table of contents: one specification per file, such as a
    state DOT `Special Specification 7049 / Water Mains` or `Item 421` document.
    The whole file becomes one section numbered by its own title block."""
    head = "\n".join(pages[0].split("\n")[:25]) if pages else ""
    m = re.search(r"^\s*(Special\s+Specification|Item)\s+(\d{3,4})\s*\n\s*([A-Za-z][^\n]{2,80})\s*$", head, re.M)
    if not m:
        return []
    prefix = "SS" if m.group(1).startswith("Special") else "Item"
    return [Section(f"{prefix} {m.group(2)}", m.group(3).strip(), start_page=1, found=True)]


def index_manual(pdf_path: str):
    pages = load_pages(pdf_path)
    sections, toc_end = parse_toc(pages)
    locate(sections, pages, skip_before=toc_end)
    discover_unlisted(sections, pages, toc_end)
    if not any(x.found for x in sections):
        sections[:] = single_item_spec(pages)
    located = [x for x in sections if x.found]
    for cur, nxt in zip(located, located[1:]):
        cur.end_page = nxt.start_page - 1
    if located:
        located[-1].end_page = len(pages)
    return pages, sections


if __name__ == "__main__":
    import sys
    pages, secs = index_manual(sys.argv[1])
    missing = [s for s in secs if not s.found]
    print(f"{len(secs)} sections in TOC, {len(secs) - len(missing)} located, {len(missing)} missing")
    for s in secs:
        flag = "" if s.found else "  <-- NOT FOUND"
        if s.toc_number:
            flag = f"  (table of contents lists this as {s.toc_number})"
        print(f"{s.number:12} p{s.start_page:>4}-{s.end_page:<4} {s.title}{flag}")
