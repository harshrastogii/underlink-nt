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
X0, WIDTH = 54.0, 488.2          # text column measured from the team's pages (54.0 to 542.2 pt)
SIZE, LEAD = 10.99, 13.5
INK = (0x1a / 255,) * 3
LABEL = (0x5c / 255, 0x5b / 255, 0x57 / 255)
FOOT = 790.0                     # running footer starts below this line
APP = "https://underlink-nt.vercel.app"
CODE = "https://github.com/harshrastogii/underlink-nt"

CHECKS = ("Automated tests check the graph counts, the headline numbers and the privacy rules. We rerun the chain "
          "classes across nine combinations of fibre radius and site radius (5, 10 and 15 km each), compare the results "
          "with outages reported in the news (Section 3.5), and check each chain's last site against the ACCC's list of "
          "Telstra mobile sites (Appendix E). One command regenerates every number and figure in this report from the "
          "shipped data.")
LIMITS = ("The ACMA register shows only licensed radio, and only 85 of Telstra's 274 NT mobile sites are on its links; "
          "fibre and satellite backhaul are missing. Fibre towns are assumed to be sound. The nearest site is not proof "
          "of the serving site, although for 16 of the 18 flagged places the chain ends at a Telstra mobile site in ACCC "
          "data (Appendix E). Replays show exposure without probabilities. Repair parameters are assumptions. Population "
          "figures are 2020 estimates, and homeland populations change with the seasons.")


def wrap(runs: list[tuple[str, bool]], width: float = WIDTH) -> list[list[tuple[str, bool]]]:
    """Greedy word wrap over (text, bold) runs with Arial metrics, like the browser's left-aligned text."""
    words = [(w, b) for text, b in runs for w in text.split()]
    space = pdfmetrics.stringWidth(" ", "Arial", SIZE)
    lines, cur, cur_w = [], [], 0.0
    for w, b in words:
        ww = pdfmetrics.stringWidth(w, "Arial-Bold" if b else "Arial", SIZE)
        if cur and cur_w + space + ww > width:
            lines.append(cur); cur, cur_w = [], 0.0
        cur_w += (space if cur else 0) + ww
        cur.append((w, b))
    return lines + [cur] if cur else lines


def overlay(paint) -> pymupdf.Document:
    """A one-page PDF drawn by reportlab. Its embedded Arial maps every character back to the
    right Unicode (PyMuPDF's insert_text maps space and hyphen to U+00A0 and U+00AD), so the
    new text can be searched and copied like the team's own text."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H), initialFontName="Arial")
    c.setFillColorRGB(*INK)
    paint(c)
    c.save()
    return pymupdf.open("pdf", buf.getvalue())


def draw(page, lines, baseline: float) -> None:
    def paint(c):
        for i, line in enumerate(lines):
            x, y = X0, H - (baseline + i * LEAD)
            runs = []                                   # consecutive words in the same font
            for w, b in line:
                if runs and runs[-1][1] == b:
                    runs[-1][0].append(w)
                else:
                    runs.append(([w], b))
            for k, (ws, b) in enumerate(runs):
                text = " ".join(ws) + (" " if k < len(runs) - 1 else "")
                font = "Arial-Bold" if b else "Arial"
                c.setFont(font, SIZE); c.drawString(x, y, text)
                x += pdfmetrics.stringWidth(text, font, SIZE)
    page.show_pdf_page(page.rect, overlay(paint), 0)


def lines_between(page, top: float, bottom: float):
    return [l for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) if top <= l["bbox"][1] and l["bbox"][3] <= bottom]


def redacted_copy(src, pno: int, rects) -> pymupdf.Document:
    one = pymupdf.open()
    one.insert_pdf(src, from_page=pno, to_page=pno)
    for r in rects:
        one[0].add_redact_annot(pymupdf.Rect(*r), fill=False)
    one[0].apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
    return one


def reflow(src, pno: int, first_line: str, runs, out) -> None:
    """Replace the paragraph starting with first_line on page pno; move what follows down to make room."""
    page = src[pno]
    para = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"])
            if t.startswith(first_line) or (para and abs(l["bbox"][1] - para[-1]["bbox"][1] - LEAD) < 1.5 and l["bbox"][0] < X0 + 1):
                para.append(l)
    top, bottom = para[0]["bbox"][1] - 1, para[-1]["bbox"][3] + 1
    baseline = para[0]["spans"][0]["origin"][1]
    new = wrap(runs)
    shift = (len(new) - len(para)) * LEAD
    below = [l["bbox"][3] for l in lines_between(page, bottom, FOOT)]
    drawings = [d["rect"].y1 for d in page.get_drawings() if bottom < d["rect"].y0 and d["rect"].y1 < FOOT]
    lowest = max(below + drawings + [bottom])
    if lowest + shift > FOOT - 8:
        raise SystemExit(f"page {pno + 1}: moving content down {shift} pt would reach {lowest + shift:.0f} pt, past the footer")
    upper = redacted_copy(src, pno, [(0, top, W, FOOT)])                  # header, text above, footer
    lower = redacted_copy(src, pno, [(0, 0, W, bottom), (0, FOOT, W, H)])  # everything after the paragraph
    p = out.new_page(width=W, height=H)
    p.show_pdf_page(p.rect, upper, 0)
    p.show_pdf_page(pymupdf.Rect(0, shift, W, H + shift), lower, 0)
    draw(p, new, baseline)
    print(f"page {pno + 1}: {len(para)} lines -> {len(new)} lines, content below moved {shift:.1f} pt (lowest now {lowest + shift:.0f} pt)")


def title_links(page) -> None:
    """Two rows under Date, in the same columns, sizes and colours as the rows above."""
    rows = (("Web app", "underlink-nt.vercel.app", APP), ("Code", "github.com/harshrastogii/underlink-nt", CODE))

    def paint(c):
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
    reflow(src, 4, "Automated tests check", [(CHECKS, False)], out)
    out.insert_pdf(src, from_page=5, to_page=7)
    reflow(src, 8, "Limitations.", [("Limitations.", True), (LIMITS, False)], out)
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
