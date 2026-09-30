"""Second round of changes to the team's report PDF (30 September 2026).

Keeps the team's design and edits only what is listed here:
  page 1   two rows under Date: the web app and the code, as clickable links
  page 5   Section 2.4 names the ACCC check (Appendix E)
  page 9   the Limitations paragraph gives the scope of the licence register and the ACCC result
  page 14  Appendix D rebuilt with the page label in the team's bold style
  15-17    Appendices E, F and G (appendix_efg.py)

A body paragraph is replaced by true redaction of the old text; everything below it
is moved down as vector content (show_pdf_page), so nothing is rasterised and
the old words cannot be found by search or copy-paste.

    python patch_report_v2.py <in.pdf (14 pages)> <out.pdf>
"""
from __future__ import annotations

import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
FD = "/System/Library/Fonts/Supplemental/"
AR, ARB = FD + "Arial.ttf", FD + "Arial Bold.ttf"
pdfmetrics.registerFont(TTFont("Arial", AR)); pdfmetrics.registerFont(TTFont("Arial-Bold", ARB))

W, H = 594.96, 841.92
X0, RIGHT = 54.0, 542.2          # text column measured from the team's pages
SIZE, LEAD = 10.99, 13.5
INK = (0x1a / 255,) * 3
LABEL = (0x5c / 255, 0x5b / 255, 0x57 / 255)
FOOT = 790.0                     # running footer starts below this line
APP = "https://underlink-nt.vercel.app"
CODE = "https://github.com/harshrastogii/underlink-nt"

BLUE = (0x2a / 255, 0x78 / 255, 0xd6 / 255)

# Body edits: (page index, first words of the paragraph, [(old text, new text), ...]).
# Substitutions apply inside the paragraph's text runs, so bold lead-ins keep their style.
EDITS = {
    4: [("Automated tests check", [(
            "(5, 10 and 15 km each), and compare the results with outages reported in the news (Section 3.5).",
            "(5, 10 and 15 km each), compare the results with outages reported in the news (Section 3.5), and check "
            "each chain's last site against the ACCC's list of Telstra mobile sites (Appendix E).")]),
        ("Of the 116 larger places", [(
            "Fibre or satellite links the register cannot show can only lower these counts, so 18 is an upper bound, "
            "and Recommendation 1 is how to check it.",
            "Fibre or satellite links the register cannot show can only remove single-path relays from these 23 chains, "
            "so for them 18 is an upper bound; such links could also join a radio island to fibre and add a chain. "
            "Recommendation 1 is how to check both.")]),
        ("Sixteen of the 18 sit inside", [
            (r"re:a solar-powered Telstra site near \w+ could not", "a solar-powered Telstra site could not"),
            (r"re:The first single-path relay on Galiwin'ku's chain .*? same site\.",
             "None of the five single-path relays on its chain is in the Hardening Program, and public data cannot show "
             "whether one of them is that solar site.")])],
    8: [("Limitations.", [(
            "The ACMA register shows only licensed radio. Fibre and satellite backhaul are missing, fibre towns are "
            "assumed to be sound, and the nearest site is not proof of the serving site.",
            "The ACMA register shows only licensed radio, and only 85 of Telstra's 274 NT mobile sites are on its links; "
            "fibre and satellite backhaul are missing. Fibre towns are assumed to be sound. The nearest site is not proof "
            "of the serving site, although for 16 of the 18 flagged places the chain ends at a Telstra mobile site in "
            "ACCC data (Appendix E).")]),
        ("DCDD's data warehouse loads", [(
            "Observed repair times then replace our assumed ones.",
            "Observed repair times then replace our assumed ones. Per-place figures stay in the restricted tier, and "
            "each community's custodian can see its own.")])],
}
# Table 2, Galiwin'ku row (page 7): cell x, first baseline, width, new runs (text, bold, colour). Same or fewer lines.
CELLS = {6: [(151.6, 690.73, 109.0, [("Solar Telstra site ran its batteries flat at night, 12 nights", False, INK)]),
             (268.8, 690.73, 138.0, [("Radio chain; 5 single-path relays, none in the Hardening Program", False, INK)]),
             (415.3, 690.73, 126.0, [("Fits,", True, BLUE), ("if the solar site is on its chain", False, INK)])]}
CELL_SIZE, CELL_LEAD = 9.49, 12.0


def wrap(runs, width, size=SIZE):
    """Greedy word wrap over (text, bold, colour) runs with Arial metrics, like the browser's left-aligned text."""
    words = [(w, b, c) for text, b, c in runs for w in text.split()]
    space = pdfmetrics.stringWidth(" ", "Arial", size)
    lines, cur, cur_w = [], [], 0.0
    for w, b, c in words:
        ww = pdfmetrics.stringWidth(w, "Arial-Bold" if b else "Arial", size)
        if cur and cur_w + space + ww > width:
            lines.append(cur); cur, cur_w = [], 0.0
        cur_w += (space if cur else 0) + ww
        cur.append((w, b, c))
    return lines + [cur] if cur else lines


def overlay(paint) -> pymupdf.Document:
    """A one-page PDF drawn by reportlab. Its embedded Arial maps every character back to the
    right Unicode (PyMuPDF's insert_text maps space and hyphen to U+00A0 and U+00AD), so the
    new text can be searched and copied like the team's own text."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H), initialFontName="Arial")
    paint(c)
    c.save()
    return pymupdf.open("pdf", buf.getvalue())


def paint_lines(c, lines, x0, baseline, size=SIZE, lead=LEAD):
    for i, line in enumerate(lines):
        x, y = x0, H - (baseline + i * lead)
        for j, (w, b, col) in enumerate(line):
            font = "Arial-Bold" if b else "Arial"
            text = w + (" " if j < len(line) - 1 else "")
            c.setFont(font, size); c.setFillColorRGB(*col); c.drawString(x, y, text)
            x += pdfmetrics.stringWidth(text, font, size)


def paragraph(page, prefix):
    """Lines of the paragraph that starts with prefix, and its text as (text, bold) runs."""
    lines = [l for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])]
    lines.sort(key=lambda l: l["bbox"][1])
    start = next(i for i, l in enumerate(lines) if "".join(s["text"] for s in l["spans"]).startswith(prefix))
    para = [lines[start]]
    for l in lines[start + 1:]:
        if abs(l["bbox"][0] - para[0]["bbox"][0]) < 1 and abs(l["bbox"][1] - para[-1]["bbox"][1] - LEAD) < 1.5:
            para.append(l)
    runs = []                                   # [text, bold], lines joined with a space unless hyphen-broken
    for k, l in enumerate(para):
        for j, sp in enumerate(l["spans"]):
            t, b = sp["text"], "Bold" in sp["font"]
            if k and j == 0 and runs and not runs[-1][0].endswith("-"):
                t = " " + t
            if runs and runs[-1][1] == b:
                runs[-1][0] += t
            else:
                runs.append([t, b])
    return para, [[" ".join(t.split()), b] for t, b in runs]


def redacted_copy(src, pno: int, rects) -> pymupdf.Document:
    one = pymupdf.open()
    one.insert_pdf(src, from_page=pno, to_page=pno)
    for r in rects:
        one[0].add_redact_annot(pymupdf.Rect(*r), fill=False)
    one[0].apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
    return one


def edit_page(src, pno: int, edits, out) -> None:
    """Rewrite paragraphs on one page. Content between and below them moves down by the lines each gains,
    as vector content; a paragraph's left margin (e.g. a recommendation number) moves with it."""
    page = src[pno]
    items = []
    for prefix, subs in edits:
        para, runs = paragraph(page, prefix)
        for old, new in subs:
            if old.startswith("re:"):               # a pattern, so the old wording need not be printed here
                pat = re.compile(old[3:])
                assert any(pat.search(t) for t, _ in runs), f"page {pno + 1}: pattern not found: {old[3:60]}"
                runs = [[pat.sub(new, t), b] for t, b in runs]
                continue
            assert any(old in t for t, _ in runs), f"page {pno + 1}: text not found: {old[:60]}"
            runs = [[t.replace(old, new), b] for t, b in runs]
        x0 = para[0]["bbox"][0]
        new = wrap([(t, b, INK) for t, b in runs], RIGHT - x0)
        items.append(dict(top=para[0]["bbox"][1] - 1, bottom=para[-1]["bbox"][3] + 1, x0=x0,
                          base=para[0]["spans"][0]["origin"][1], lines=new, grow=(len(new) - len(para)) * LEAD))
    items.sort(key=lambda d: d["top"])
    shift, pieces = 0.0, []
    for i, it in enumerate(items):
        prev = items[i - 1]["bottom"] if i else None
        rects = ([(0, 0, W, prev)] if prev else []) + [(it["x0"] - 1, it["top"], W, it["bottom"]), (0, it["bottom"], W, H if i else FOOT)]
        pieces.append((redacted_copy(src, pno, rects), shift))
        it["shift"] = shift
        shift += it["grow"]
    pieces.append((redacted_copy(src, pno, [(0, 0, W, items[-1]["bottom"]), (0, FOOT, W, H)]), shift))
    below = [l["bbox"][3] for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) if items[-1]["bottom"] < l["bbox"][1] < FOOT]
    lowest = max(below + [d["rect"].y1 for d in page.get_drawings() if items[-1]["bottom"] < d["rect"].y0 and d["rect"].y1 < FOOT] + [items[-1]["bottom"]])
    if lowest + shift > FOOT - 8:
        raise SystemExit(f"page {pno + 1}: content would reach {lowest + shift:.0f} pt, past the footer")
    p = out.new_page(width=W, height=H)
    for doc, dy in pieces:
        p.show_pdf_page(pymupdf.Rect(0, dy, W, H + dy), doc, 0)
    p.show_pdf_page(p.rect, overlay(lambda c: [paint_lines(c, it["lines"], it["x0"], it["base"] + it["shift"]) for it in items]), 0)
    print(f"page {pno + 1}: {len(items)} paragraphs rewritten, content below moved {shift:.1f} pt (lowest now {lowest + shift:.0f} pt)")


def edit_cells(page, cells) -> None:
    """Replace table cell text in place; the new text must not need more lines than the old."""
    for x0, base, width, runs in cells:
        old = [l for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
               if abs(l["bbox"][0] - x0) < 1 and base - 12 < l["spans"][0]["origin"][1] < base + 60]
        old = [l for i, l in enumerate(sorted(old, key=lambda l: l["bbox"][1]))
               if i == 0 or abs(l["spans"][0]["origin"][1] - base - i * CELL_LEAD) < 1.5]
        new = wrap(runs, width, CELL_SIZE)
        assert len(new) <= len(old), f"cell at {x0} needs {len(new)} lines, has {len(old)}"
        page.add_redact_annot(pymupdf.Rect(x0 - 0.5, old[0]["bbox"][1] - 0.5, x0 + width + 4, old[-1]["bbox"][3] + 0.5), fill=False)
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        page.show_pdf_page(page.rect, overlay(lambda c, n=new: paint_lines(c, n, x0, base, CELL_SIZE, CELL_LEAD)), 0)


def title_links(page) -> None:
    """Two rows under Date, in the same columns, sizes and colours as the rows above."""
    rows = (("Web app", "underlink-nt.vercel.app", APP), ("Code", "github.com/harshrastogii/underlink-nt", CODE))

    def paint(c):
        # the U logo beside the 20 pt title "Underlink" (title box 54-146 pt wide, 378.6-401 pt down)
        logo = HERE.parents[1] / "docs" / "assets" / "underlink_logo.png"
        h = 22.0
        c.drawImage(str(logo), 154.0, H - 400.0, width=h * 900 / 651, height=h, mask="auto")
        c.setFont("Arial", SIZE)
        for i, (label, text, _) in enumerate(rows):
            y = H - (564.74 + 22.5 * (i + 1))
            c.setFillColorRGB(*LABEL); c.drawString(54.0, y, label)
            c.setFillColorRGB(*INK); c.drawString(150.37, y, text)
    page.show_pdf_page(page.rect, overlay(paint), 0)
    for i, (_, text, url) in enumerate(rows):
        y = 564.74 + 22.5 * (i + 1)
        w = pdfmetrics.stringWidth(text, "Arial", SIZE)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(150.37, y - 9.5, 150.37 + w, y + 2.5), "uri": url})


def main(src_path: str, out_path: str) -> None:
    src = pymupdf.open(src_path)
    assert len(src) == 14, f"expected the 14-page report, got {len(src)} pages"
    out = pymupdf.open()
    out.insert_pdf(src, from_page=0, to_page=3)
    title_links(out[0])
    edit_page(src, 4, EDITS[4], out)
    out.insert_pdf(src, from_page=5, to_page=7)
    edit_cells(out[6], CELLS[6][0:3])
    edit_page(src, 8, EDITS[8], out)
    out.insert_pdf(src, from_page=9, to_page=12)
    with tempfile.TemporaryDirectory() as tmp:
        d, efg = Path(tmp) / "d.pdf", Path(tmp) / "efg.pdf"
        subprocess.run([sys.executable, str(HERE / "appendix_d.py"), str(d), "14"], check=True)
        subprocess.run([sys.executable, str(HERE / "appendix_efg.py"), str(efg), "15"], check=True)
        out.insert_pdf(pymupdf.open(d))
        out.insert_pdf(pymupdf.open(efg))
    out.set_metadata({**src.metadata, "modDate": pymupdf.get_pdf_now()})
    out.save(out_path, garbage=3, deflate=True)
    print("wrote", out_path, "pages:", len(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
