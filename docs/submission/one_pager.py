"""One-page plain-English summary of Underlink (A4 PDF, Arial).

    python docs/submission/one_pager.py <output.pdf>
Numbers are read from outputs/public/numbers.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[2]
N = json.loads((ROOT / "outputs/public/numbers.json").read_text())
c, r, rep, fb = N["chains"], N["relays"], N["repair"], N["fallbacks"]

FD = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", FD + "Arial.ttf")); pdfmetrics.registerFont(TTFont("Arial-Bold", FD + "Arial Bold.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")
INK, MUTED, BLUE, ORANGE, DARK = (colors.HexColor(h) for h in ("#1a1a1a", "#555555", "#2a78d6", "#eb6834", "#12303b"))

S = {
    "title": ParagraphStyle("t", fontName="Arial-Bold", fontSize=22, leading=25, textColor=DARK),
    "sub": ParagraphStyle("s", fontName="Arial-Bold", fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=2),
    "by": ParagraphStyle("b", fontName="Arial", fontSize=9, leading=12, textColor=MUTED, spaceBefore=3, spaceAfter=6),
    "h": ParagraphStyle("h", fontName="Arial-Bold", fontSize=11.5, leading=14, textColor=DARK, spaceBefore=6, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=10.3, leading=13.4, textColor=INK, spaceAfter=3),
    "li": ParagraphStyle("li", fontName="Arial", fontSize=10.3, leading=13.4, textColor=INK, leftIndent=13, bulletIndent=1, spaceAfter=2),
    "foot": ParagraphStyle("f", fontName="Arial", fontSize=8.5, leading=11, textColor=MUTED, spaceBefore=6),
}


def diagram(width):
    """Town with a fibre cable, a line of towers on hills, then the community."""
    h = 58
    d = Drawing(width, h)
    y = 30
    d.add(Rect(0, y - 11, 22, 22, fillColor=BLUE, strokeColor=None))
    d.add(String(11, 6, "Town with", fontName="Arial", fontSize=7.5, fillColor=INK, textAnchor="middle"))
    d.add(String(11, -3, "fibre cable", fontName="Arial", fontSize=7.5, fillColor=INK, textAnchor="middle"))
    xs = [66 + i * 42 for i in range(6)]
    d.add(Line(22, y, xs[-1] + 60, y, strokeColor=MUTED, strokeWidth=1.4))
    for i, x in enumerate(xs):
        d.add(Circle(x, y, 7, fillColor=ORANGE if 1 <= i <= 4 else colors.white, strokeColor=ORANGE if 1 <= i <= 4 else INK, strokeWidth=1.3))
    d.add(String((xs[1] + xs[4]) / 2, y + 16, "weak links: towers with no way around them", fontName="Arial-Bold", fontSize=8, fillColor=ORANGE, textAnchor="middle"))
    d.add(String(xs[0], 6, "tower", fontName="Arial", fontSize=7.5, fillColor=MUTED, textAnchor="middle"))
    cx = xs[-1] + 66
    d.add(Circle(cx, y, 17, fillColor=colors.HexColor("#eaf2fc"), strokeColor=BLUE, strokeWidth=1))
    d.add(Circle(cx, y, 4, fillColor=INK, strokeColor=None))
    d.add(String(cx, 6, "Community", fontName="Arial-Bold", fontSize=7.5, fillColor=INK, textAnchor="middle"))
    d.add(String(cx, -3, "covered on the map", fontName="Arial", fontSize=7.5, fillColor=BLUE, textAnchor="middle"))
    tx = cx + 34
    for k, line in enumerate(["If any orange tower", "stops working, the", "community loses phone", "service, even when its", "own tower is fine."]):
        d.add(String(tx, y + 20 - k * 9.5, line, fontName="Arial", fontSize=8, fillColor=INK))
    return d


def build(out: str) -> None:
    ppl = f"{round(c['people_ge1_spof'], -2):,}"
    dry_fast = rep["jul_bands"].get("<1 d", 0); wet_slow = rep["jan_bands"].get(">14 d", 0)
    story = [
        Paragraph("Underlink", S["title"]),
        Paragraph("What happens to phone service in remote NT communities on the day it breaks", S["sub"]),
        Paragraph("Team DIC017: Harsh Rastogi and Aashish. CDU IT Code Fair 2026, Data Innovation Challenge.", S["by"]),

        Paragraph("The problem", S["h"]),
        Paragraph("A remote community's mobile tower has to pass calls and internet on to the rest of the phone network. In much of "
                  "the Northern Territory it does this through a line of radio towers on hills, each passing the signal to the next, "
                  "until the signal reaches a town with a fibre cable. If one tower in that line stops working, every community "
                  "further along can lose service, even when its own tower is fine.", S["p"]),
        Paragraph("Coverage maps do not show this. They show where a phone should get signal on a normal day. Wadeye counts as "
                  "covered, yet it lost service on and off for nine weeks in early 2026 after floods damaged its cable and cut "
                  "power. People could not call 000 or top up their prepaid power cards.", S["p"]),
        Spacer(1, 4), diagram(17.2 * cm), Spacer(1, 6),

        Paragraph("What we did", S["h"]),
        Paragraph("The Australian Communications and Media Authority publishes a list of licensed radio links. We used it to rebuild "
                  "these lines of towers across the NT. For each community we traced the line back to a town with fibre and found "
                  "every tower with no way around it. We call these weak links. Then we checked four things: which past cyclones "
                  "came near them, whether any backup power for them is on public record, how long a repair crew might take to "
                  "reach them in the wet and dry seasons, and what still works in the community when the phones are down.", S["p"]),

        Paragraph("What we found", S["h"]),
        Paragraph(f"Of {c['radio_chain_places']} larger communities that rely on a line of radio towers, {c['with_ge1_spof']} "
                  f"(about {ppl} people) depend on at least one weak link. Telstra's coverage map shows "
                  f"{c['ge1_spof_inside_predicted_4g']} of those {c['with_ge1_spof']} as covered.", S["li"], bulletText="•"),
        Paragraph(f"None of the {r['spof_relays']} weak links is in the government program that pays for better backup power, "
                  "so nobody outside the phone company knows how long their batteries last.", S["li"], bulletText="•"),
        Paragraph(f"In the dry season, {dry_fast} of the {rep['radio_chain_places']} communities would be reconnected within a day. "
                  f"In the wet season, {wet_slow} could wait weeks, because a tower on their line is more than 10 km from a "
                  "sealed road.", S["li"], bulletText="•"),
        Paragraph(f"Only {fb['radio_chain_with_other_carrier']} of the {rep['radio_chain_places']} has a second phone company's "
                  "tower nearby that could carry a 000 call.", S["li"], bulletText="•"),

        Paragraph("Who it helps", S["h"]),
        Paragraph("Communities get a one-page \"When the phone goes down\" card that shows what still works and where to go. The NT "
                  "Government gets numbers for each region and a short list of facts to ask phone companies for. Phone companies "
                  "get a private list of the towers to check first. All of it works without internet.", S["p"]),

        Paragraph("How we treat communities' information", S["h"]),
        Paragraph("We used public information only and studied towers and cables. Our public results never name or rank "
                  "communities, and nothing about a community is shared without the approval of someone that community "
                  "chooses. No community has reviewed this work yet, so the card is a draft to design together with them.", S["p"]),

        Paragraph("What we recommend", S["h"]),
        Paragraph("When the NT Government helps pay for new towers, it asks phone companies to share how each tower connects, "
                  "how long its batteries last, and its outage history.", S["li"], bulletText="1."),
        Paragraph(f"Before each wet season, check the batteries at the {r['far_from_sealed_road']} weak links that sit more than "
                  "10 km from a sealed road.", S["li"], bulletText="2."),
        Paragraph("Work with one community that wants to take part to redesign the card together.", S["li"], bulletText="3."),

        Paragraph("Try it: underlink-nt.vercel.app. Code: github.com/harshrastogii/underlink-nt. The full report, slides "
                  "and code are in our submission (DataChallenge_Team_DIC017_Submission.zip).", S["foot"]),
    ]
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=1.9 * cm, rightMargin=1.9 * cm, topMargin=1.5 * cm, bottomMargin=1.2 * cm,
                            title="Underlink in plain English", author="Team DIC017")
    doc.initialFontName = "Arial"
    doc.build(story)


if __name__ == "__main__":
    build(sys.argv[1])
    print("wrote", sys.argv[1])
