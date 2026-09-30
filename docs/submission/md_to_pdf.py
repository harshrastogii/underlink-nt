"""Render a Markdown file (headings, paragraphs, lists, code blocks, tables)
to an A4 PDF in Arial. Used to ship README.pdf alongside README.md.

    python docs/submission/md_to_pdf.py README.md README.pdf "Team DIC017"
"""
from __future__ import annotations

import re
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

FD = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", FD + "Arial.ttf")); pdfmetrics.registerFont(TTFont("Arial-Bold", FD + "Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", FD + "Arial Italic.ttf")); pdfmetrics.registerFont(TTFont("Mono", FD + "Courier New.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold")
INK, MUTED, RULE = colors.HexColor("#1a1a1a"), colors.HexColor("#555555"), colors.HexColor("#bfc5cc")
S = {
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=18, leading=22, textColor=INK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=13, leading=16, textColor=INK, spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Arial-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=6, spaceAfter=3, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=10, leading=13.5, textColor=INK, spaceAfter=5),
    "li": ParagraphStyle("li", fontName="Arial", fontSize=10, leading=13.5, textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=2),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.5, leading=10.5, textColor=INK, backColor=colors.HexColor("#f2f4f6"), borderPadding=4, spaceBefore=3, spaceAfter=7),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=9, leading=11, textColor=INK),
}


def inline(t: str) -> str:
    t = escape(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)                       # links -> text
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="Mono">\1</font>', t)
    return t


def convert(src: str, out: str, team: str) -> None:
    lines = open(src, encoding="utf-8").read().splitlines()
    story, i, W = [], 0, A4[0] - 4 * cm
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            block = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i]); i += 1
            story.append(Preformatted("\n".join(block), S["code"])); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append([Paragraph(inline(c), S["cell"]) for c in cells])
                i += 1
            t = Table(rows, colWidths=[W / len(rows[0])] * len(rows[0]), repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, RULE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf5")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, -1), "Arial")]))
            story += [t, Spacer(1, 6)]; continue
        m = re.match(r"^(#{1,3}) (.*)", ln)
        if m:
            story.append(Paragraph(inline(m.group(2)), S["h%d" % len(m.group(1))]))
        elif re.match(r"^\s*[-*] ", ln):
            story.append(Paragraph(inline(re.sub(r"^\s*[-*] ", "", ln)), S["li"], bulletText="•"))
        elif re.match(r"^\d+\. ", ln):
            n, rest = ln.split(" ", 1)
            story.append(Paragraph(inline(rest), S["li"], bulletText=n))
        elif ln.strip():
            para = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|\s*[-*] |\d+\. )", lines[i + 1]):
                i += 1; para.append(lines[i])
            story.append(Paragraph(inline(" ".join(para)), S["p"]))
        i += 1

    def page(c, d):
        c.saveState(); c.setFont("Arial", 8.5); c.setFillColor(MUTED)
        c.drawString(2 * cm, 1.2 * cm, f"Underlink  |  {team}  |  README"); c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {c.getPageNumber()}")
        c.restoreState()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Underlink README", author=team)
    doc.initialFontName = "Arial"
    doc.build(story, onFirstPage=page, onLaterPages=page)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    print("wrote", sys.argv[2])
