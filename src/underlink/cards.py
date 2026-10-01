"""Community card: "When the phone goes down".

Draws a one-page A4 PDF for a synthetic "Sample Community" only. Cell values
come from config/rules.yaml, so the card and the rules never disagree.
The card carries no project branding and names no real community.

Run:  PYTHONPATH=src python -m underlink.cards
"""
from __future__ import annotations

import io
from pathlib import Path

import yaml
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from underlink.config import OUTPUTS, ROOT

RULES_PATH = ROOT / "config" / "rules.yaml"
OUT_PDF = OUTPUTS / "community_samples" / "sample_card.pdf"

COMMUNITY = "Sample Community"
AS_AT = "Information as at 29 September 2026"
TITLE = "When the phone goes down"
WATERMARK = "ILLUSTRATIVE SAMPLE - NOT FOR DISTRIBUTION"

# Card columns -> scenario keys in rules.yaml
COLUMNS = [("Normal day", "normal_day"),
           ("Tower or line down", "tower_or_line_down"),
           ("Power down", "community_power_down")]

# Colour-blind safe fills (blue / orange / greys), with a text colour that
# keeps contrast on each fill. The word in the cell always carries the meaning.
INK = HexColor("#1b1f24")
MUTED = HexColor("#4a525c")
FILL = {
    "works": (HexColor("#2a78d6"), white),
    "degraded": (HexColor("#b9d7f5"), INK),
    "not available": (HexColor("#eb6834"), INK),
    "ask locally": (HexColor("#dedede"), INK),
}

WHERE_TO_GO = [
    "Satellite Wi-Fi phone: [location to be added by community]",
    "Sky Muster at the school or evacuation centre",
    "Payphone: ask locally whether it works when the tower is down",
]
SAT_TEXT = ("Satellite texting works outdoors with a clear view of the sky, on some "
            "phones and plans. It cannot reach 000. From December 2027 more phones may "
            "get outdoor calls and texts, if the law passes.")
CHECKLIST = [
    "Charge power banks",
    "Know your nearest working phone",
    "Save clinic and council numbers",
    "Know who to tell when the phone is down",
]
LANG_NOTE = ("To be written and voiced by community members with paid interpreters "
             "(Aboriginal Interpreter Service). No machine translation.")
FOOTER = ("Draft for co-design. Built from public information. No community has "
          "reviewed this card. Is this right? Tell your community's chosen contact.")
ROAD_NOTE = "Road cut: repairs take longer. Ask locally what still works."


def load_rules(path: Path = RULES_PATH) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def cell_word(rule: dict) -> str:
    """Word printed in a grid cell: the optional label, else the status."""
    return (rule.get("label") or rule["status"]).upper()


def source_line(rules: dict) -> str:
    """One-line source list, built from the sources the rules actually cite."""
    short = {
        "acma_000": "ACMA, Emergency calls",
        "telstra_sat_msg": "Telstra, Satellite Messaging",
        "uomo_bill": "Parliament of Australia, UOMO Bill",
        "abc_wadeye_2026": "ABC News 7 Apr 2026",
        "abc_east_arnhem_2020": "ABC News 12 Oct 2020",
        "secure_nt_cyclone": "SecureNT, Cyclone warnings",
    }
    return "Sources: " + "; ".join(short.values()) + "."


class _Card:
    """Thin wrapper over a reportlab canvas that records every string drawn."""

    def __init__(self, fh):
        self.c = canvas.Canvas(fh, pagesize=A4, pageCompression=1)
        self.c.setTitle(TITLE)
        self.c.setAuthor("Draft for co-design")
        self.strings: list[str] = []

    def text(self, x, y, s, font="Helvetica", size=10, color=INK, align="left"):
        self.strings.append(s)
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        if align == "center":
            self.c.drawCentredString(x, y, s)
        else:
            self.c.drawString(x, y, s)

    def para(self, x, y, s, width, font="Helvetica", size=10, lead=None, color=INK):
        """Wrap s to width, draw top-down from baseline y, return next baseline."""
        lead = lead or size * 1.25
        for line in simpleSplit(s, font, size, width):
            self.text(x, y, line, font, size, color)
            y -= lead
        return y

    def box(self, x, y, w, h, stroke=INK, fill=None, lw=1.2, r=6):
        self.c.setLineWidth(lw)
        self.c.setStrokeColor(stroke)
        if fill is not None:
            self.c.setFillColor(fill)
        self.c.roundRect(x, y, w, h, r, stroke=1, fill=1 if fill is not None else 0)


# --- pictograms: simple line drawings in a 22 x 22 box, origin bottom-left ---

def _icon(c, kind, x, y):
    c.saveState()
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(1.6)
    if kind == "call_000":          # handset
        c.roundRect(x + 6, y + 1, 10, 20, 2, stroke=1, fill=0)
        c.line(x + 9, y + 18, x + 13, y + 18)
        c.circle(x + 11, y + 4.5, 1.2, stroke=0, fill=1)
    elif kind == "warnings":        # warning triangle with "!"
        p = c.beginPath()
        p.moveTo(x + 11, y + 21); p.lineTo(x + 21, y + 2); p.lineTo(x + 1, y + 2); p.close()
        c.drawPath(p, stroke=1, fill=0)
        c.line(x + 11, y + 14, x + 11, y + 8)
        c.circle(x + 11, y + 5, 1.1, stroke=0, fill=1)
    elif kind == "telehealth":      # medical cross
        c.rect(x + 8, y + 2, 6, 18, stroke=0, fill=1)
        c.rect(x + 2, y + 8, 18, 6, stroke=0, fill=1)
    elif kind == "eftpos":          # bank card
        c.roundRect(x + 1, y + 4, 20, 14, 2, stroke=1, fill=0)
        c.rect(x + 1, y + 12, 20, 3, stroke=0, fill=1)
        c.line(x + 4, y + 7.5, x + 10, y + 7.5)
    elif kind == "centrelink":      # office building
        p = c.beginPath()
        p.moveTo(x + 1, y + 15); p.lineTo(x + 11, y + 21); p.lineTo(x + 21, y + 15); p.close()
        c.drawPath(p, stroke=1, fill=0)
        for cx in (x + 4, x + 10, x + 16):
            c.rect(cx, y + 4, 2.2, 10, stroke=0, fill=1)
        c.line(x + 1, y + 2.5, x + 21, y + 2.5)
    elif kind == "power_topup":     # lightning bolt
        p = c.beginPath()
        p.moveTo(x + 13, y + 21); p.lineTo(x + 5, y + 10); p.lineTo(x + 11, y + 10)
        p.lineTo(x + 8, y + 1); p.lineTo(x + 17, y + 13); p.lineTo(x + 11, y + 13); p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "school_online":   # open book
        c.line(x + 11, y + 3, x + 11, y + 18)
        p = c.beginPath()
        p.moveTo(x + 11, y + 18); p.curveTo(x + 7, y + 20, x + 4, y + 20, x + 1, y + 18)
        p.lineTo(x + 1, y + 3); p.curveTo(x + 4, y + 5, x + 7, y + 5, x + 11, y + 3)
        p.curveTo(x + 15, y + 5, x + 18, y + 5, x + 21, y + 3); p.lineTo(x + 21, y + 18)
        p.curveTo(x + 18, y + 20, x + 15, y + 20, x + 11, y + 18)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def draw(fh, rules: dict | None = None) -> list[str]:
    """Draw the card into file-like fh. Returns every string drawn, in order."""
    rules = rules or load_rules()
    k = _Card(fh)
    c = k.c
    W, H = A4
    M = 36                      # page margin
    CW = W - 2 * M              # content width

    # 1. Header
    y = H - M - 24
    k.text(M, y, TITLE, "Helvetica-Bold", 26)
    y -= 24
    k.text(M, y, COMMUNITY, "Helvetica-Bold", 15)
    k.text(W - M - c.stringWidth(AS_AT, "Helvetica", 10), y, AS_AT, "Helvetica", 10, MUTED)
    y -= 10
    c.setStrokeColor(INK); c.setLineWidth(1.5); c.line(M, y, W - M, y)

    # 2. Grid: services x scenarios, values from rules.yaml
    label_w = 176
    col_w = (CW - label_w) / len(COLUMNS)
    row_h, head_h, gap = 36, 22, 3
    y -= 8 + head_h
    for i, (name, _) in enumerate(COLUMNS):
        k.text(M + label_w + i * col_w + col_w / 2, y + 7, name, "Helvetica-Bold", 11,
               align="center")
    for svc in rules["services"]:
        y -= row_h
        _icon(c, svc["id"], M + 2, y + (row_h - 22) / 2)
        k.text(M + 32, y + row_h / 2 - 4, svc["label"], "Helvetica-Bold", 12)
        for i, (_, key) in enumerate(COLUMNS):
            rule = svc["rules"][key]
            fill, ink = FILL[rule["status"]]
            cx = M + label_w + i * col_w
            k.box(cx + gap, y + gap, col_w - 2 * gap, row_h - 2 * gap, stroke=fill,
                  fill=fill, lw=0.5, r=3)
            k.text(cx + col_w / 2, y + row_h / 2 - 4, cell_word(rule), "Helvetica-Bold",
                   11, ink, align="center")
    y -= 15
    k.text(M, y, ROAD_NOTE, "Helvetica", 10, MUTED)

    # 3. Triple Zero box (left) and Where to go box (right)
    y -= 12
    half = (CW - 12) / 2
    bh = 142
    top = y
    k.box(M, top - bh, half, bh, stroke=INK, lw=2.2)
    k.text(M + 10, top - 20, "Triple Zero (000)", "Helvetica-Bold", 14)
    k.para(M + 10, top - 37, rules["triple_zero_text"], half - 20, "Helvetica", 11, 14)

    rx = M + half + 12
    k.box(rx, top - bh, half, bh)
    k.text(rx + 10, top - 20, "Where to go", "Helvetica-Bold", 14)
    yy = top - 38
    for item in WHERE_TO_GO:
        c.setFillColor(INK); c.circle(rx + 14, yy + 3.5, 2, stroke=0, fill=1)
        yy = k.para(rx + 22, yy, item, half - 32, "Helvetica", 10.5, 13) - 6

    # 4. Satellite texting box, full width
    y = top - bh - 10
    sh = 50
    k.box(M, y - sh, CW, sh, stroke=HexColor("#2a78d6"), fill=HexColor("#eef5fd"))
    k.text(M + 10, y - 17, "Satellite texting", "Helvetica-Bold", 12)
    k.para(M + 118, y - 17, SAT_TEXT, CW - 128, "Helvetica", 10, 12.5)

    # 5. Before the wet checklist (left) and blank language panel (right)
    y = y - sh - 10
    ph = 136
    k.box(M, y - ph, half, ph)
    k.text(M + 10, y - 20, "Before the wet", "Helvetica-Bold", 14)
    yy = y - 42
    for item in CHECKLIST:
        c.setStrokeColor(INK); c.setLineWidth(1); c.rect(M + 10, yy - 2, 11, 11)
        k.text(M + 28, yy, item, "Helvetica", 11)
        yy -= 21

    c.setDash(4, 3)
    k.box(rx, y - ph, half, ph, lw=1.2)
    c.setDash()
    k.text(rx + 10, y - 20, "In our words / language", "Helvetica-Bold", 14)
    k.para(rx + 10, y - ph + 30, LANG_NOTE, half - 20, "Helvetica-Oblique", 8.5, 10.5,
           MUTED)

    # 6. Footer
    y = M + 28
    c.setStrokeColor(MUTED); c.setLineWidth(0.6); c.line(M, y + 14, W - M, y + 14)
    y = k.para(M, y, FOOTER, CW, "Helvetica-Bold", 9.5, 12)
    k.para(M, y - 2, source_line(rules), CW, "Helvetica", 7.5, 9, MUTED)

    # 7. Diagonal watermark, drawn last and faint so the content stays readable
    c.saveState()
    c.translate(W / 2, H / 2)
    c.rotate(52)
    k.text(0, -14, WATERMARK, "Helvetica-Bold", 34,
           Color(0.33, 0.33, 0.33, alpha=0.10), align="center")
    c.restoreState()

    c.showPage()
    c.save()
    return k.strings


def card_strings() -> list[str]:
    """Every string drawn on the card, without writing a file (used by tests)."""
    return draw(io.BytesIO())


def build(out: Path = OUT_PDF, community: str = COMMUNITY, release=None) -> Path:
    """Write the card. The made-up Sample Community needs no release; a card for a real
    community is written only after its custodian has released it (governance.require_release)."""
    if community != COMMUNITY:
        from underlink.governance import require_release
        require_release(release, community)
        raise NotImplementedError("Cards for real communities are drawn only after co-design (Recommendation 6).")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        draw(fh)
    return out


if __name__ == "__main__":
    p = build()
    print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.0f} KB)")
