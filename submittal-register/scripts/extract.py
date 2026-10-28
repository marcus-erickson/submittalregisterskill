"""Deterministic first-pass submittal extraction.

For every located section this finds the SUBMITTALS article in Part 1, splits
it into lettered items, and classifies each item by type. It also flags
candidate submittals buried in Parts 2 and 3 (mock-ups, test reports,
certificates, warranties) for review.
"""
import csv
import re
import sys

from specindex import index_manual

# Lines that repeat on every page (footers, running headers). Project specific
# patterns can be passed in; the number-dash-page footer is generic.
FOOTER = re.compile(r"^\s*(?:\d{2}\s\d{2}\s\d{2}(?:\.\d+)?\s*[-–]\s*\d+|\d{5,6}\.\d+)\s*$")

ARTICLE = re.compile(
    r"^\s*(?:(\d{1,2}(?:\.\d{1,2})?)\.?\s+)?"
    r"((?:[A-Z][A-Za-z&,/\-]*\s+){0,2}(?:SUBMITTALS?(?:\s+DATA)?|SHOP\s+DRAWINGS(?:,[A-Z ,&]+)?|FABRICATION\s+DRAWINGS|PRODUCT\s+DATA|SAMPLES)(?:\s*[-–(][^\n:]{0,30})?):?\s*$",
    re.I | re.M,
)
ANY_ARTICLE = re.compile(
    r"^\s*(?:\d\.\d{1,2}\s+[A-Z][A-Za-z0-9 ,&/\-–'.()]{3,}|\d{1,2}\.\s+[A-Z][A-Z0-9 ,&/\-–'.()]{3,}|[A-Z][A-Z &,/\-]{3,40}):?\s*$",
    re.M,
)
PART = re.compile(r"^\s*PART\s+([123])\b", re.I | re.M)
ITEM = re.compile(r"^\s{0,14}([A-Za-z])(?:\.\s+|\s{2,})(\S.*)$")
SUBITEM = re.compile(r"^\s{2,}(?:\((\d{1,2})\)|(\d{1,2})\.)\s+(\S.*)$")

TYPE_RULES = [
    ("WD", r"wiring diagram|ladder[- ]type|control diagram|schematic"),
    ("RECORD", r"record\s+drawings?|as-?built|project\s+record\s+documents"),
    ("SD", r"shop\s+drawings?|fabrication drawings?|coordination drawings?|erection drawings?|layout drawings?|installation drawings?|dimensioned drawings?|detailed drawings?|drawings (?:showing|indicating)|scaled (?:layout )?drawings?"),
    ("PD", r"product\s+data|manufacturer'?s?\s+(?:technical\s+)?(?:product\s+)?data|catalog|cut sheets?|literature|data sheets?|technical data|(?:manufacturer'?s?\s+)?installation\s+instructions|manufacturer'?s?\s+instructions"),
    ("SAM", r"\bsamples?\b"),
    ("CALC", r"calculations?|\bcalcs?\b|engineering analysis|\banalys[ei]s\b|delegated\s+design"),
    ("CERT", r"certificat|certification|qualification|affidavit|compliance letter|licen[sc]e|declaration|documentation of iso"),
    ("TEST", r"test\s+reports?|test\s+results?|field\s+(?:quality|test)|inspection reports?|testing and balancing|balance reports?|mix design"),
    ("WARR", r"warrant"),
    ("OM", r"maintenance\s+(?:data|manuals?|instructions)|operation(?:s)?\s+and\s+maintenance|\bO\s?&\s?M\b|operating instructions|spare parts"),
    ("MOCKUP", r"mock-?ups?"),
    ("SCHED", r"schedule of|submittals? schedule|progress schedule|\b(?:product|glazing|finish|door|hardware|room|equipment|color)\s+schedule|schedule:"),
    ("REPORT", r"survey|statement of|\b(?:work|management|action|waste)\s+plan\b|\bplan:|photograph|video|inventory|design mix|proposed protection|\breports?\b"),
]
TYPE_RX = [(k, re.compile(v, re.I)) for k, v in TYPE_RULES]

BURIED = re.compile(
    r"(mock-?ups?|submit[^.\n]{0,80}(?:test report|certificate|certification|warrant|sample|shop drawing|product data)|"
    r"(?:test report|certificate|warrant)[^.\n]{0,60}(?:shall be )?submitted)",
    re.I,
)


def detect_noise(pages, zone=4, min_share=0.03, prefix_share=0.06, prefix_len=8):
    """Find header and footer lines that repeat across many pages.

    Looks only at the first and last few non-empty lines of each page. A line is
    noise when its digit-stripped text repeats on enough pages, or, for lines
    that contain a digit (dates, page numbers), when its first few characters
    repeat on many pages even though the tail changes with the section title.
    """
    from collections import Counter
    strip = lambda l: re.sub(r"[\d\s]+", " ", l).strip().lower()
    exact, prefix = Counter(), Counter()
    for p in pages:
        lines = [l for l in p.split("\n") if l.strip()]
        zl = [l for l in lines[:zone] + lines[-zone:] if len(l.strip()) > 8]
        exact.update({strip(l) for l in zl})
        prefix.update({strip(l)[:prefix_len] for l in zl if re.search(r"\d", l)})
    n = len(pages)
    bad_exact = {k for k, c in exact.items() if c >= max(6, int(n * min_share))}
    bad_prefix = {k for k, c in prefix.items() if c >= max(10, int(n * prefix_share))}
    structural = re.compile(r"^\s*(PART\s+\d|SECTION\s+\d|\d\.\d|[A-Za-z]\.\s|\d{1,2}\.\s|END OF SECTION)", re.I)

    def is_noise(line):
        if structural.match(line):
            return False
        k = strip(line)
        return k in bad_exact or (bool(re.search(r"\d", line)) and k[:prefix_len] in bad_prefix)

    return is_noise


FOOTER_TAIL = re.compile(
    r"\S.*\s(?:\d{5,6}\.\d+|\d{2}\s\d{2}\s\d{2}(?:\.\d+)?\s*[-–]\s*\d+)\s*$"
)


def clean(text: str, noise) -> str:
    out = []
    for line in text.split("\n"):
        if FOOTER.match(line) or FOOTER_TAIL.match(line) or (noise and noise(line)):
            continue
        out.append(line.rstrip())
    return "\n".join(out)


def classify(text: str) -> list[str]:
    head = text[:160]
    found = []
    for k, rx in TYPE_RX:
        m = rx.search(head)
        if m:
            found.append((m.start(), k))
    found.sort()
    seen, out = set(), []
    for _, k in found:
        if k not in seen:
            seen.add(k)
            out.append(k)
    if not out:  # nothing in the lead phrase, look at the whole item
        for k, rx in TYPE_RX:
            if rx.search(text):
                out.append(k)
    if not out:
        if re.match(r"\s*(see|refer to|in accordance with|comply with|provide submittals in accordance)\b", text, re.I) or \
           re.search(r"submittals? (?:procedures|in accordance with)", text[:120], re.I):
            return ["REF"]
    return out or ["OTHER"]


def classify_with_context(text, group, article_title):
    """Classify by the item text, else by its group heading, else by the article title."""
    t = classify(text)
    if t in (["OTHER"], ["REF"]):
        for ctx in (group, article_title):
            c = classify(ctx or "")
            if c not in (["OTHER"], ["REF"]) and c != ["SCHED"] and c != ["OM"] and (t == ["OTHER"]):
                return c
    return t


def is_div01_procedure(sec):
    return sec.number.startswith("01") and bool(
        re.search(r"submittal|shop drawings", sec.title, re.I)
    )


def section_text(pages, sec, noise):
    lo, hi = sec.start_page, sec.end_page
    txt = "\n".join(pages[lo - 1:hi])
    return clean(txt, noise)


def _wrapped_line(text: str, pos: int) -> bool:
    """True when the line at `pos` continues the line above it (for example a wrapped `PROCEDURES:`),
    because a real article heading follows a blank line."""
    if re.match(r"\s*\d", text[pos:pos + 12]):
        return False  # numbered headings are real, even inside a table of contents
    prev_end = text.rfind("\n", 0, pos)  # newline that ends the previous line
    if prev_end <= 0:
        return False
    prev_start = text.rfind("\n", 0, prev_end) + 1
    return bool(text[prev_start:prev_end].strip())


def submittal_articles(text: str):
    """Return (article_ref, title, body, start_offset, end_offset) for each SUBMITTALS article, any part."""
    part_pos = [m.start() for m in PART.finditer(text)]
    p2_first = next((m.start() for m in PART.finditer(text) if m.group(1) == "2"), len(text))
    out = []
    for m in ARTICLE.finditer(text):
        g1 = m.group(1)
        if g1 is None or "." not in g1:
            if m.group(2).upper() != m.group(2):
                continue  # "4." or unnumbered headings must be all caps, otherwise it is a list item
        if g1 is None and ("SUBMITTAL" not in m.group(2).upper() or m.start() >= p2_first):
            continue  # unnumbered headings count only when they are SUBMITTALS in Part 1
        end = len(text)
        nxt = ANY_ARTICLE.search(text, m.end())
        while nxt and _wrapped_line(text, nxt.start()):
            nxt = ANY_ARTICLE.search(text, nxt.end())
        if nxt:
            end = min(end, nxt.start())
        for pp in part_pos:
            if pp > m.end():
                end = min(end, pp)
                break
        out.append((g1 or "", m.group(2).strip(), text[m.end():end], m.start(), end))
    return out


SD_HEAD = re.compile(r"^\s*SD-(\d{2})\s+(\S.*?)\s*$")
PAGE_FOOT = re.compile(r"^\s*SECTION\s+[\dA-Z .]+\s+Page\s+\d+\s*$", re.I)
GOVT_CLASS = re.compile(r"\s*;\s*([A-Z]{1,3}(?:\s*,\s*[A-Z]{1,3})*)\s*$")
WRAP_MIN = 60  # a wrapped line runs to about column 70
SD_PROSE = re.compile(r"^(?:Submit|Include|Provide|Furnish|As applicable|Provide the following|Note)\b|:\s*$")
# an SD-list entry that reads like a sentence, not an item name: probably explanatory text, so it is flagged
SD_SENTENCE = re.compile(r"^.{91,}[.]$|\b(?:shall|must|should)\b|^(?:Prior to|Where|Indicate|Certify|Written|A copy of)\b")
SD_END = re.compile(r"^\s*(?:PART\s+\d\b|\d{1,2}\.\d{1,2}(?:\.\d+)*\s+\S)")
SD_TYPE = {"02": "SD", "03": "PD", "04": "SAM", "05": "CALC", "06": "TEST", "07": "CERT",
           "08": "PD", "09": "TEST", "10": "OM"}


def parse_sd_items(body: str):
    """Federal (UFGS) style: `SD-03 Product Data` headings with one item per paragraph beneath,
    each optionally ending in `; G` (government approval) or `; S`. One row per item."""
    items, head, block, prev_len = [], None, [], 0

    def flush():
        nonlocal block
        if block and head:
            text = " ".join(block)
            if items and text[:1].islower() and items[-1]["sd"] == head[0] and not GOVT_CLASS.search(items[-1]["text"]):
                items[-1]["text"] += " " + text  # wrapped across a page break
            else:
                items.append({"letter": f"SD-{head[0]}", "text": text, "group": f"SD-{head[0]} {head[1]}", "sd": head[0]})
        block = []

    for line in body.split("\n"):
        if PAGE_FOOT.match(line):
            flush()
            continue
        if head and SD_END.match(line):
            break  # the list is over, the next numbered paragraph or Part has started
        m = SD_HEAD.match(line)
        if m:
            flush()
            head = (m.group(1), m.group(2))
            continue
        if not line.strip():
            flush()
            continue
        if head:
            parts = re.split(r"(?<=;\s[GS])(?=[A-Z][a-z])", line.strip())  # two items run together: `...; GBracing`
            if len(parts) > 1:
                for part in parts:
                    if block:
                        flush()
                    block.append(part)
                prev_len = len(line.rstrip())
                continue
            # Items are usually separated by a blank line, but some sections list them on consecutive
            # lines. A line that ends in a `; G` marker, or a short line (it did not reach the right
            # margin, so it was not wrapped), closes the item.
            if block and (GOVT_CLASS.search(block[-1]) or prev_len < WRAP_MIN):
                flush()
            block.append(line.strip())
            prev_len = len(line.rstrip())
    flush()
    items = [it for it in items if not SD_PROSE.search(it["text"])]
    for it in items:
        m = GOVT_CLASS.search(it["text"])
        it["classification"] = ""
        if m:
            it["classification"] = re.sub(r"\s+", "", m.group(1))
            it["text"] = it["text"][:m.start()].strip()
    return items


def parse_items(body: str):
    """Split an article into items. A short lettered heading such as
    `A. Submittals for Review:` with numbered children yields the children."""
    sd_items = parse_sd_items(body)
    if sd_items:
        return sd_items
    tops, cur, sub = [], None, None
    for line in body.split("\n"):
        if not line.strip():
            continue
        mi = ITEM.match(line)
        if mi and (cur is None or ord(mi.group(1).lower()) >= ord(cur["letter"].lower())):
            cur = {"letter": mi.group(1), "text": mi.group(2).strip(), "kids": []}
            tops.append(cur)
            sub = None
            continue
        ms = SUBITEM.match(line)
        if ms and cur is not None:
            sub = {"num": ms.group(1) or ms.group(2), "text": ms.group(3).strip()}
            cur["kids"].append(sub)
        elif sub is not None:
            sub["text"] += " " + line.strip()
        elif cur is not None:
            cur["text"] += " " + line.strip()
    items = []
    for t in tops:
        heading_like = t["kids"] and (len(t["text"]) < 80 or re.search(r"as\s+listed\s+below|as\s+follows\s*[.:]?\s*$", t["text"], re.I))
        if heading_like:
            for k in t["kids"]:
                items.append({"letter": f"{t['letter']}.{k['num']}", "text": k["text"], "group": t["text"].rstrip(": ")})
        else:
            text = t["text"] + "".join(f" {k['num']}. {k['text']}" for k in t["kids"])
            items.append({"letter": t["letter"], "text": text, "group": ""})
    if not items and body.strip():
        items = parse_decimal_items(body)
    if not items and body.strip():
        items.append({"letter": "", "text": " ".join(body.split()), "group": ""})
    return items


DECIMAL_ITEM = re.compile(r"^\s{0,6}(\d{1,2}(?:\.\d{1,2})+)\.?\s+(\S.*)$")


def parse_decimal_items(body: str):
    """Items numbered 2.1, 2.1.1 (state DOT specifications). A numbered parent whose
    children follow becomes the group heading and the children become the items."""
    raw, cur = [], None
    for line in body.split("\n"):
        if not line.strip():
            continue
        m = DECIMAL_ITEM.match(line)
        if m:
            cur = {"letter": m.group(1), "text": m.group(2).strip()}
            raw.append(cur)
        elif cur is not None:
            cur["text"] += " " + line.strip()
    out = []
    for i, it in enumerate(raw):
        kids = [k for k in raw[i + 1:] if k["letter"].startswith(it["letter"] + ".")]
        if kids:
            continue
        parent = next((p for p in reversed(raw[:i]) if it["letter"].startswith(p["letter"] + ".")), None)
        out.append({"letter": it["letter"], "text": it["text"], "group": parent["text"].split(".")[0][:60] if parent else ""})
    return out


def page_of(cp, bounds, first_page, off, needle=""):
    """Page number for a character offset in the joined section text.

    `cp` is the list of cleaned pages, `bounds` the start offset of each page in
    the joined text. If `needle` is given, the page is refined by searching from
    the page where the article starts, so repeated text maps to the right page.
    """
    import bisect
    idx = max(0, bisect.bisect_right(bounds, off) - 1)
    if needle:
        key = needle[:40]
        for i in range(idx, len(cp)):
            if key in " ".join(cp[i].split()) or key in cp[i]:
                return first_page + i
    return first_page + idx


def extract(pdf, noise=None):
    pages, sections = index_manual(pdf)
    if not any(s.found for s in sections):
        import sys
        print("No specification sections were found in this file. It may be a cover letter, a scanned "
              "document (no text layer), or a manual without a table of contents or SECTION headers.", file=sys.stderr)
    noise = noise or detect_noise(pages)
    rows, flags = [], []
    for sec in sections:
        if not sec.found:
            flags.append((sec.number, sec.title, "listed in the table of contents but not found in this PDF (another volume or an addendum?)"))
            continue
        cp = [clean(p, noise) for p in pages[sec.start_page - 1:sec.end_page]]
        text = "\n".join(cp)
        bounds, pos = [], 0
        for p in cp:
            bounds.append(pos)
            pos += len(p) + 1
        arts = submittal_articles(text)
        if not arts:
            flags.append((sec.number, sec.title, "no SUBMITTALS article found"))
        for ref, atitle, body, off, end in arts:
            for it in parse_items(body):
                t = " ".join(it["text"].split())
                rows.append({
                    "section": sec.number,
                    "section_title": sec.title,
                    "article": (f"{ref} {it['letter']}" if it["letter"].startswith("SD-") else
                                it["letter"] if re.match(r"\d+\.\d", it["letter"]) else
                                ".".join(x for x in (ref, it["letter"]) if x)) or "-",
                    "article_title": atitle.title(),
                    "group": it["group"],
                    "types": SD_TYPE.get(it.get("sd", ""), "") or "+".join(classify_with_context(t, it["group"], atitle)),
                    "requirement": t,
                    "page": page_of(cp, bounds, sec.start_page, off, " ".join(it["text"].split())),
                    "classification": it.get("classification", ""),
                    "source": ("Division 01 procedure" if is_div01_procedure(sec) else
                               "REVIEW: sentence in SD list" if it.get("sd") and SD_SENTENCE.search(t) else
                               "Submittals article"),
                })
        spans = [(a[3], a[4]) for a in arts]
        body_start = next((m.start() for m in PART.finditer(text) if m.group(1) == "1"), 0)
        if not arts:
            for pos_, t in leadin_items(text, spans, body_start):
                t = " ".join(t.split())
                rows.append({
                    "section": sec.number, "section_title": sec.title,
                    "article": "no submittals article", "article_title": "Typed item outside a submittals article",
                    "group": "", "types": "+".join(classify(t)), "requirement": t,
                    "page": page_of(cp, bounds, sec.start_page, pos_, t), "source": "REVIEW: no article",
                })
        buried_iter = [] if (is_div01_procedure(sec) or sec.number[:2] in ("00", "01")) else BURIED.finditer(text, body_start)
        for m in buried_iter:
            if any(lo <= m.start() < hi for lo, hi in spans):
                continue
            s0 = max(0, m.start() - 60)
            snippet = " ".join(text[s0:m.end() + 140].split())
            rows.append({
                "section": sec.number,
                "section_title": sec.title,
                "article": "outside article",
                "article_title": "Possible submittal outside the submittals article",
                "group": "",
                "types": "+".join(classify(m.group(0))),
                "requirement": snippet,
                "page": page_of(cp, bounds, sec.start_page, m.start()),
                "source": "REVIEW: buried requirement",
            })
    return rows, flags, sections


LEADIN = re.compile(
    r"^\s{0,16}(?:[A-Z]|\d{1,2})\.\s+((?:Product Data|Manufacturer.s Data|Shop Drawings|Samples?|Wiring Diagrams?|"
    r"Test Reports?|Certificates?|Calculations|Maintenance Data|Warranty)[^:\n]{0,40}):\s+(.*)$",
    re.I | re.M,
)


def leadin_items(text, spans, body_start):
    out = []
    for m in LEADIN.finditer(text, body_start):
        if any(lo <= m.start() < hi for lo, hi in spans):
            continue
        j = text.find("\n", m.end())
        j = len(text) if j == -1 else j
        k = m.end()
        # include wrapped continuation lines until the next list item or blank line
        rest = text[k:].split("\n")
        cont = []
        for ln in rest[1:4]:
            if not ln.strip() or re.match(r"^\s{0,16}(?:[A-Z]|\d{1,2})\.\s", ln) or re.match(r"^\s*\d\.\d", ln):
                break
            cont.append(ln.strip())
        out.append((m.start(), " ".join([m.group(1) + ": " + m.group(2)] + cont)))
    return out


FIELDS = ["section", "section_title", "article", "article_title", "group", "types", "requirement", "page", "classification", "source"]

if __name__ == "__main__":
    pdf, out = sys.argv[1], sys.argv[2]
    rows, flags, sections = extract(pdf)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    core = [r for r in rows if r["source"] == "Submittals article"]
    print(f"{len(rows)} rows ({len(core)} from submittal articles, {len(rows) - len(core)} buried candidates)")
    print(f"{len(flags)} located sections with no submittals article:")
    for f in flags:
        print("  ", *f)
