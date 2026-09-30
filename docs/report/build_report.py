"""Build the challenge report (DOCX + PDF) from underlink_report.md.

Formatting follows the organisers' rules: A4, Arial, title 20 pt bold, section
headings 14 pt bold, body 11 pt, captions and references 10 pt, team number and
page number in both header and footer, continuous page numbering.

    python docs/report/build_report.py            # writes DOCX and PDF
The team number comes from TEAM below; change it once the organisers confirm it.
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE / "underlink_report.md"
TEAM = yaml.safe_load(SRC.read_text().split("---", 2)[1])["team"].replace("[", "").replace("]", "").strip()
OUT_STEM = f"DataChallenge_{TEAM}_Report"
FONT = "Arial"
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x55, 0x55, 0x55)
CONTENT_CM = 17.0                     # A4 width 21 cm minus 2 cm margins


# ---------------------------------------------------------------- helpers
def set_cell_shading(cell, hex_fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def add_field(run, instr: str) -> None:
    """Insert a Word field (e.g. PAGE) into a run."""
    for tag, text in (("begin", None), ("instr", instr), ("separate", None), ("end", None)):
        if tag == "instr":
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = text
        else:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag)
        run._r.append(el)
        if tag == "separate":
            t = OxmlElement("w:t"); t.text = "1"; run._r.append(t)


def fmt_run(run, size=11, bold=False, italic=False, color=INK, font=FONT):
    run.font.name = font; run.font.size = Pt(size); run.font.bold = bold; run.font.italic = italic
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), font)


def add_inline(par, text: str, size=11, color=INK, italic=False):
    """Add text with **bold** spans."""
    for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if chunk:
            fmt_run(par.add_run(chunk), size=size, bold=(i % 2 == 1), italic=italic, color=color)


def para(doc_or_cell, text="", size=11, bold=False, align=None, space_after=6, space_before=0, italic=False, color=INK, keep_next=False):
    p = doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after); pf.space_before = Pt(space_before); pf.line_spacing = 1.08
    pf.keep_with_next = keep_next
    if align:
        p.alignment = align
    if text:
        if bold:
            fmt_run(p.add_run(text), size=size, bold=True, italic=italic, color=color)
        else:
            add_inline(p, text, size=size, color=color, italic=italic)
    return p


def png_size(path: Path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    return struct.unpack(">II", head[16:24])


def add_image(container, path: Path, width_cm: float):
    p = container.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2); p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    return p


def caption(doc, text):
    return para(doc, text, size=10, color=MUTED, space_after=10)


def table(doc, rows, caption_text):
    para(doc, caption_text, size=10, color=MUTED, space_after=3, keep_next=True)
    header, body = rows[0], rows[1:]
    t = doc.add_table(rows=len(rows), cols=len(header))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = t.cell(r_i, c_i)
            cell.text = ""
            p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
            add_inline(p, val.strip(), size=9.5, color=INK)
            if r_i == 0:
                for run in p.runs:
                    run.font.bold = True
                set_cell_shading(cell, "E6EDF5")
    # light grey borders
    tbl = t._tbl
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), "BFC5CC")
        borders.append(el)
    tbl.tblPr.append(borders)
    para(doc, "", space_after=4)


def header_footer(section):
    for hf, align_title in ((section.header, True), (section.footer, False)):
        hf.is_linked_to_previous = False
        p = hf.paragraphs[0]; p.text = ""
        p.paragraph_format.tab_stops.add_tab_stop(Cm(CONTENT_CM), WD_TAB_ALIGNMENT.RIGHT)
        left = "Underlink: Revealing the Hidden Dependencies Behind NT Connectivity" if align_title else "CDU IT Code Fair 2026, Data Innovation Challenge"
        fmt_run(p.add_run(left), size=9, color=MUTED)
        fmt_run(p.add_run(f"\t{TEAM}  |  Page "), size=9, color=MUTED)
        r = p.add_run(); fmt_run(r, size=9, color=MUTED); add_field(r, "PAGE")


# ---------------------------------------------------------------- build
def build():
    text = SRC.read_text()
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.0))
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    sec.header_distance, sec.footer_distance = Cm(1.0), Cm(1.0)
    header_footer(sec)
    normal = doc.styles["Normal"]; normal.font.name = FONT; normal.font.size = Pt(11)

    # Title page
    para(doc, "", space_after=90)
    para(doc, meta["title"], size=20, bold=True, space_after=4)
    para(doc, meta["subtitle"], size=14, bold=True, color=RGBColor(0x2A, 0x5B, 0x9A), space_after=24)
    para(doc, meta["kind"], size=11, space_after=2)
    para(doc, meta["event"], size=11, space_after=18)
    para(doc, meta["team"], size=11, bold=True, space_after=4)
    for m in meta["members"]:
        para(doc, m, size=11, space_after=2)
    para(doc, meta["date"], size=11, space_before=14, space_after=150)
    para(doc, meta["acknowledgement"], size=10, color=MUTED, italic=True)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    lines = body.strip("\n").splitlines()
    i, list_counter = 0, 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1; continue
        if line.startswith("# "):
            title = line[2:].strip()
            if title in ("References",) or title.startswith("Appendix A"):
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            para(doc, title, size=14, bold=True, space_before=10, space_after=6, keep_next=True)
            list_counter = 0
        elif line.startswith("## "):
            para(doc, line[3:].strip(), size=11, bold=True, space_before=6, space_after=3, keep_next=True)
        elif line.startswith("TABLE:"):
            cap = line[len("TABLE:"):].strip(); rows = []
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells).strip()) <= set("-: "):
                    rows.append(cells)
                i += 1
            table(doc, rows, cap); continue
        elif line.startswith("FIGURES:"):
            left, right, width, cap = [x.strip() for x in line[len("FIGURES:"):].split("|", 3)]
            t = doc.add_table(rows=1, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for cell, img in zip(t.rows[0].cells, (left, right)):
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.paragraphs[0].add_run().add_picture(str(ROOT / img), width=Cm(float(width)))
            caption(doc, cap)
        elif line.startswith("FIGURE:"):
            img, width, cap = [x.strip() for x in line[len("FIGURE:"):].split("|", 2)]
            add_image(doc, ROOT / img, float(width)); caption(doc, cap)
        elif line.startswith("CODE:"):
            i += 1
            while i < len(lines) and lines[i].strip():
                p = para(doc, "", space_after=0); fmt_run(p.add_run(lines[i]), size=10, font=FONT)
                i += 1
            para(doc, "", space_after=4); continue
        elif re.match(r"^\d+\. ", line):
            n, rest = line.split(" ", 1)
            in_refs = any(l.strip() == "# References" for l in lines[:i]) and not any(l.startswith("# Appendix") for l in lines[:i])
            size = 10 if in_refs else 11
            p = para(doc, "", size=size, space_after=3 if in_refs else 4)
            p.paragraph_format.left_indent = Cm(0.7); p.paragraph_format.first_line_indent = Cm(-0.7)
            fmt_run(p.add_run(f"{n}\t" if not in_refs else f"[{n[:-1]}]\t"), size=size, color=INK)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.7))
            add_inline(p, rest, size=size)
        else:
            para(doc, line, size=11, space_after=6)
        i += 1

    out_docx = HERE / f"{OUT_STEM}.docx"
    doc.save(out_docx)
    # The PDF is drawn by build_pdf.py; this file is the editable copy.
    print("wrote", out_docx)


if __name__ == "__main__":
    sys.exit(build())
