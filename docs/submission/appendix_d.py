"""Appendix D (New Zealand comparison, researched by Aashish) as one A4 page
styled to match the team's redesigned report: Arial, 9 pt grey header and
footer, 14 pt bold heading, 11 pt body, tables with a dark rule under the
header row and light rules between rows. Facts checked on 30 September 2026.

    python appendix_d.py <out.pdf> <page_number>
"""
from __future__ import annotations

import sys

from reportlab.lib.colors import Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Spacer, Table, TableStyle

FD = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", FD + "Arial.ttf")); pdfmetrics.registerFont(TTFont("Arial-Bold", FD + "Arial Bold.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")

W, H = 594.96, 841.92                        # the team's page size
LEFT, RIGHT = 54.0, 542.2
INK = Color(0.102, 0.102, 0.102); GREY = Color(0.541, 0.537, 0.518); HEAD = Color(0.361, 0.357, 0.341)   # #1a1a1a, #8a8984, #5c5b57
RULE_LIGHT = Color(0.839, 0.835, 0.816)

S = {
    "h": ParagraphStyle("h", fontName="Arial-Bold", fontSize=13.99, leading=17, textColor=INK, spaceAfter=7),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=10.99, leading=13.5, textColor=INK, spaceAfter=7),
    "cap": ParagraphStyle("cap", fontName="Arial-Bold", fontSize=10, leading=12.5, textColor=INK, spaceAfter=4),
    "th": ParagraphStyle("th", fontName="Arial-Bold", fontSize=9, leading=11, textColor=HEAD),
    "td": ParagraphStyle("td", fontName="Arial", fontSize=9.49, leading=11.6, textColor=INK),
    "src": ParagraphStyle("src", fontName="Arial", fontSize=8.5, leading=10.3, textColor=INK, leftIndent=22, firstLineIndent=-22, spaceAfter=1),
}

ROWS = [
    ("Every reported fault is mapped live",
     "Chorus, New Zealand's main wholesale fixed-line network, publishes a public map of all reported faults, searchable by address, "
     "with estimated restoration times. It updates every 10 minutes [D1].", "Rec 3; Rec 1 (outage logs)"),
    ("Small rural providers log outages and their causes",
     "WiFiConnect, a rural wireless provider on the West Coast, keeps a dated public list of outages by repeater. One entry reports "
     "continuous rain causing power problems at its Mt French repeaters [D2].", "Rec 2; Rec 1"),
    ("A mobile carrier maps planned and unplanned outages",
     "One NZ's network status map covers mobile and Rural Broadband services and lists a power cut at a cell site as one cause of "
     "unplanned outages [D3].", "Rec 1; Rec 3"),
    ("Publicly funded rural towers are shared and carry backup power",
     "Crown Infrastructure Partners approves towers built by the Rural Connectivity Group, which Spark, One NZ and 2degrees own. Its "
     "2024 annual report lists 513 rural and black-spot towers live and describes a site with 30 solar panels and a backup generator [D4].",
     "Rec 1"),
    ("Public money pays for backhaul resilience",
     "The same report says the West Coast and Southland fibre links, finished in 2023, increased network resilience and enabled 18 "
     "towers on State Highway 6 and 8 on the Milford Road [D4].", "Rec 1; Rec 2"),
    ("Schools and clinics come first, and towers must be shared",
     "The Rural Broadband Initiative prioritised schools, hospitals and health centres, and every new tower had to allow other "
     "operators to co-locate [D5].", "Rec 1; Rec 6"),
    ("The regulator's map shows coverage only",
     "The Commerce Commission's connectivity map shows where providers say service is available and what people connect with. "
     "Providers self-report the data, it is updated once a year, and it has no backhaul, backup-power or outage layer [D6].",
     "Finding in Section 3.1"),
    ("Telehealth guidance stops at getting connected",
     "The New Zealand Telehealth Forum explains how rural clinics can connect but gives no advice on what to do when the link "
     "fails [D7].", "Community card (Rec 6)"),
]

SOURCES = [
    "Chorus Limited (2026). Internet outages map. Retrieved 30 September 2026. https://www.chorus.co.nz/optimise/internet-outages-map",
    "WiFiConnect Ltd (2026). Network status: outages. Retrieved 30 September 2026. https://wificonnect.co.nz/outages/",
    "One New Zealand (2026). Our network status. Retrieved 30 September 2026. https://one.nz/help/network-status/",
    "Crown Infrastructure Partners (2024). Annual Report 2024, year ended 30 June 2024. https://nationalinfrastructure.govt.nz/wp-content/uploads/Crown-Infrastructure-Partners-Annual-Report-2024-Online-2.pdf",
    "Ministry of Business, Innovation and Employment (2016). Rural Broadband Initiative Phase 1, August 2016. https://www.mbie.govt.nz/assets/0b55b27a15/rural-broadband-initiative-phase-1-august-2016.pdf",
    "Commerce Commission New Zealand (2025). Telecommunications connectivity map, data as at 30 June 2025. https://www.comcom.govt.nz/regulated-industries/telecommunications/monitoring-the-telecommunications-market/telecommunications-connectivity-map/",
    "New Zealand Telehealth Forum and Resource Centre. Internet connectivity in rural areas. https://www.telehealth.org.nz/telehealth-resources/technology/technology/internet-connectivity-in-rural-areas/",
]


def header_footer(c, page: int) -> None:
    """Running header and footer as on the team's pages: grey 9 pt text left, bold ink page label right."""
    label = f"Team DIC017 | Page {page}"
    c.setFillColor(GREY); c.setFont("Arial", 9)
    c.drawString(53.85, 793.17, "Underlink: Revealing the Hidden Dependencies Behind NT Connectivity")
    c.drawString(53.85, 34.17, "CDU IT Code Fair 2026, Data Innovation Challenge")
    c.setFillColor(INK); c.setFont("Arial-Bold", 9)
    c.drawRightString(542.24, 793.17, label)
    c.drawRightString(542.24, 34.17, label)


def build(out: str, page: int) -> None:
    c = canvas.Canvas(out, pagesize=(W, H), initialFontName="Arial")
    c.setTitle("Appendix D: What New Zealand already publishes")
    # header and footer exactly where the team's pages have them
    header_footer(c, page)

    tw = RIGHT - LEFT
    data = [[Paragraph("Practice in New Zealand", S["th"]), Paragraph("Evidence", S["th"]), Paragraph("Supports", S["th"])]]
    data += [[Paragraph(a, S["td"]), Paragraph(b, S["td"]), Paragraph(r, S["td"])] for a, b, r in ROWS]
    t = Table(data, colWidths=[tw * 0.25, tw * 0.56, tw * 0.19], repeatRows=1)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
             ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("FONTNAME", (0, 0), (-1, -1), "Arial"),
             ("LINEBELOW", (0, 0), (-1, 0), 0.75, INK)]
    style += [("LINEBELOW", (0, i), (-1, i), 0.75, RULE_LIGHT) for i in range(1, len(data))]
    t.setStyle(TableStyle(style))

    story = [
        Paragraph("Appendix D: What New Zealand already publishes", S["h"]),
        Paragraph("Aashish compared the NT with New Zealand, which also has remote rural areas, shared rural towers and severe "
                  "weather. We checked every fact below against its source on 30 September 2026. The comparison supports "
                  "Recommendations 1 to 3 and the community card.", S["p"]),
        Paragraph('<font name="Arial-Bold" color="#1a1a1a">Table D1.</font> New Zealand practice that bears on Underlink\'s '
                  'recommendations.', ParagraphStyle("capd", fontName="Arial", fontSize=10, leading=12.5, textColor=HEAD, spaceAfter=5)),
        t, Spacer(1, 8),
        Paragraph("None of the New Zealand sources we checked shows which towers depend on a single backhaul path. That is the gap "
                  "Underlink fills for the NT.", S["p"]),
        Paragraph("Sources for Appendix D", S["cap"]),
    ]
    story += [Paragraph(f"[D{i}]&nbsp;&nbsp;{s}", S["src"]) for i, s in enumerate(SOURCES, 1)]
    frame = Frame(LEFT, 52, tw, 757.17 + 14 - 52, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
    leftover = frame.addFromList(story, c)
    if story:
        raise SystemExit(f"Appendix D does not fit on one page: {len(story)} blocks left over")
    c.showPage(); c.save()
    print("wrote", out)


if __name__ == "__main__":
    build(sys.argv[1], int(sys.argv[2]))
