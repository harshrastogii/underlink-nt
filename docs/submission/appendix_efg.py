"""Appendices E, F and G, styled like the team's report (see appendix_d.py).

E  the ACCC check of the serving-site assumption
F  a measure and a starting value for each recommendation
G  links: code, web app and the 18 datasets

Every number is read from outputs/public/numbers.json or data/manifest.csv.

    python appendix_efg.py <out.pdf> <first_page_number>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from reportlab.graphics import shapes
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).parent))
from appendix_d import GREY, HEAD, INK, RULE_LIGHT, S, header_footer  # noqa: E402  (registers Arial too)

shapes.STATE_DEFAULTS["fontName"] = "Arial"      # graphics default is Times-Roman; keep the PDF Arial-only

ROOT = Path(__file__).resolve().parents[2]
N = json.loads((ROOT / "outputs/public/numbers.json").read_text())
A, C, R, FB, CF = N["accc_check"], N["chains"], N["relays"], N["fallbacks"], N["coverage_flags"]
APP = "https://underlink-nt.vercel.app"
CODE = "https://github.com/harshrastogii/underlink-nt"

W, H = 594.96, 841.92
LEFT, RIGHT = 54.0, 542.2
TW = RIGHT - LEFT
MUTED = Color(0.361, 0.357, 0.341)

ST = dict(S)
ST["cap"] = ParagraphStyle("cap2", fontName="Arial", fontSize=10, leading=12.5, textColor=MUTED, spaceAfter=5, spaceBefore=2)
ST["h"] = ParagraphStyle("h2", parent=S["h"], spaceBefore=0)
ST["link"] = ParagraphStyle("link", fontName="Arial", fontSize=9.49, leading=11.6, textColor=INK)


def cap(label: str, text: str) -> Paragraph:
    """Caption as on the team's pages: bold ink label, grey text."""
    return Paragraph(f'<font name="Arial-Bold" color="#1a1a1a">{label}</font> {text}', ST["cap"])


def table(rows, widths, header=True) -> Table:
    data = [[c if not isinstance(c, str) else Paragraph(c, S["th"] if (header and i == 0) else S["td"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=[TW * w for w in widths], repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
             ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("FONTNAME", (0, 0), (-1, -1), "Arial")]
    if header:
        style.append(("LINEBELOW", (0, 0), (-1, 0), 0.75, INK))
    style += [("LINEBELOW", (0, i), (-1, i), 0.75, RULE_LIGHT) for i in range(1 if header else 0, len(data))]
    t.setStyle(TableStyle(style))
    return t


def p(text: str) -> Paragraph:
    return Paragraph(text, S["p"])


def appendix_e() -> list:
    unmatched = A["ge1_spof_places"] - A["ge1_spof_end_is_mobile_site"]
    return [
        Paragraph("Appendix E: Checking the serving-site assumption", ST["h"]),
        p("The model takes the nearest licensed radio site within 10 km as the site that serves a place (Section 2.2). "
          "The ACCC's 2026 mobile infrastructure data lists each carrier's mobile sites [3], so we checked whether each "
          "radio chain ends at a Telstra mobile site. Shipped coordinates are rounded to about 1 km, so a match means a "
          f"listed Telstra site within {A['match_km']} km."),
        cap("Table E1.", "The nearest-site assumption against ACCC site data."),
        table([["Check", "Result"],
               ["Radio-chain places whose chain ends at a Telstra mobile site", f"{A['radio_chain_end_is_mobile_site']} of {A['radio_chain_places']}"],
               ["Places with a single-path relay whose chain ends at a Telstra mobile site", f"{A['ge1_spof_end_is_mobile_site']} of {A['ge1_spof_places']}"],
               ["Distance from each unmatched chain end to the nearest Telstra mobile site", f"{int(A['unmatched_min_km'])} km or more"],
               [f"Telstra NT mobile sites within {A['match_km']} km of a licensed radio site in the graph",
                f"{A['telstra_sites_on_radio_graph']} of {A['telstra_mobile_sites_2026']} ({round(100 * A['share_on_radio_graph'])}%)"]],
              [0.78, 0.22]),
        Spacer(1, 8),
        p(f"For {A['ge1_spof_end_is_mobile_site']} of the {A['ge1_spof_places']} places, the chain ends where the community's "
          f"mobile service starts. The other {unmatched} end far from any listed Telstra site. They may be served by a site on "
          f"fibre or satellite. If so, the count of {C['with_ge1_spof']} falls, which fits Section 3.1: {C['with_ge1_spof']} is an upper bound. "
          "Any match distance from 1.5 to 3 km gives the same counts, because every unmatched chain end is at least "
          f"{int(A['unmatched_min_km'])} km from a listed site."),
        p(f"The last row sets the scope. About {round(10 * (1 - A['share_on_radio_graph']))} in 10 of Telstra's NT mobile sites "
          "connect through fibre, satellite or links the register does not show, so Underlink describes the licensed-radio "
          "part of the network only. The check is section 5b of pipeline.py, its numbers are under accc_check in "
          "numbers.json, and test_accc_crosscheck pins them."),
    ]


def appendix_f() -> list:
    rows = [["Recommendation", "Measure", "Starting value", "Target"],
            ["1. Carrier data as a condition of co-investment",
             "Single-path relays with backhaul type, battery hours and a three-year outage log held by DCDD",
             f"0 of {R['spof_relays']} in public data", f"All {R['spof_relays']} before the 2027-28 wet season"],
            ["2. Battery check before each wet season",
             f"Share of the {R['far_from_sealed_road']} single-path relays more than 10 km from a sealed road with confirmed battery hours",
             f"0 of {R['far_from_sealed_road']} public", "Reported by 1 November each year"],
            ["3. Outage KPI in the DCDD warehouse", "Outage hours per radio-chain place per wet season",
             "Not published per place", "Loaded monthly from carrier outage registers into fact_outage_event"],
            ["4. Refresh NT connectivity registers", "Places in the 2021 register with no recorded mobile status",
             f"{CF['register_not_recorded']} of {CF['all']}", 'Every register carries an "as at" date'],
            ["5. Keep and document payphones", "Radio-chain places with a payphone within 3 km whose backhaul is public",
             f"0 of {FB['radio_chain_with_payphone_3km']}", "Published for each payphone the card lists"],
            ["6. Test the card with one community", "Communities that have reviewed and control their card", "0",
             "One community that chooses to take part, after the 2026-27 wet season"]]
    return [
        Paragraph("Appendix F: Measures and starting values", ST["h"]),
        p("Each recommendation in Section 5 has a measure. Public data gives its starting value today. DCDD could track all "
          "six in the star schema Underlink already writes (docs/schema.sql)."),
        cap("Table F1.", "A measure, a starting value and a target for each recommendation."),
        table(rows, [0.25, 0.37, 0.16, 0.22]),
    ]


def datasets() -> list[tuple[str, str, str]]:
    """(name, publisher, url) per source, as in the web app's list."""
    seen, out = set(), []
    with open(ROOT / "data/manifest.csv") as fh:
        for r in csv.DictReader(fh):
            name = r["source"].split(" public layers")[0] if "Mapping Tool" in r["source"] else r["source"]
            if name.startswith("NTLIS"):
                name = "NTLIS land council boundaries and counter disaster areas"
            if name not in seen:
                seen.add(name)
                pub = r["publisher"].replace("Department of Infrastructure, Transport, Regional Development, Communications, "
                                             "Sport and the Arts", "DITRDCSA")   # as in the report's Table 1
                out.append((name, pub.replace("Northern Territory Government (NTLIS)", "NTG"), r["url"]))
    out += [("Australian Digital Inclusion Index 2025", "RMIT University and partners", "https://digitalinclusionindex.org.au/"),
            ("Census of Population and Housing (TableBuilder)", "Australian Bureau of Statistics",
             "https://www.abs.gov.au/statistics/microdata-tablebuilder/tablebuilder")]
    return out


ORGANISER = ("ACMA Register", "NTG remote communities with mobile coverage 2021", "ACCC Mobile Infrastructure",
             "BoM tropical cyclone", "First Nations Connectivity Mapping Tool", "nbn footprint", "Australian Digital", "Census")


def qr(url: str, size: float = 78) -> Drawing:
    w = QrCodeWidget(url, barLevel="M")
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(w)
    return d


def appendix_g() -> list:
    link = lambda u: f'<a href="{u}" color="#1a1a1a">{u}</a>'   # noqa: E731
    top = Table([[[Paragraph(f'<font name="Arial-Bold">Web app</font> (public numbers only): {link(APP)}', S["p"]),
                   Paragraph(f'<font name="Arial-Bold">Code</font>: {link(CODE)}', S["p"])],
                  qr(APP)]], colWidths=[TW - 90, 90])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("FONTNAME", (0, 0), (-1, -1), "Arial"),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    rows = [["Dataset (publisher)", "Link"]]
    for name, pub, url in datasets():
        star = "*" if name.startswith(ORGANISER) else ""
        rows.append([f"{name}{star} ({pub})", Paragraph(link(url), ST["link"])])
    return [
        Paragraph("Appendix G: Code, web app and data links", ST["h"]),
        top,
        p("The web app shows the same numbers as this report, read from numbers.json by scripts/export_web_data.py. It adds "
          "a \"break a link\" demonstration on a made-up network, the draft community card and the measures in Appendix F. "
          "It shows no relay location, site identifier or per-place result, and a test checks this. The public code "
          "repository leaves out data/processed/, because with the code those tables rebuild the restricted relay register; "
          "the ZIP sent to the organisers includes them. Appendix A applies to the web app too: Claude helped write its "
          "HTML, CSS and JavaScript."),
        CondPageBreak(120),
        cap("Table G1.", "The 18 data sources. An asterisk marks the eight the organisers suggested. Licences are in "
                         "DATA_LICENCES.md."),
        table(rows, [0.47, 0.53]),
    ]


def build(out: str, first_page: int) -> int:
    doc = BaseDocTemplate(out, pagesize=(W, H), leftMargin=LEFT, rightMargin=W - RIGHT, topMargin=H - 771.2,
                          bottomMargin=52, title="Underlink appendices E to G", author="Team DIC017", initialFontName="Arial")
    frame = Frame(LEFT, 52, TW, 771.2 - 52, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame],
                                       onPage=lambda c, d: header_footer(c, first_page + d.page - 1))])
    story = appendix_e() + [Spacer(1, 14)] + appendix_f() + [CondPageBreak(300)] + appendix_g()
    doc.build(story)
    from pypdf import PdfReader
    n = len(PdfReader(out).pages)
    print("wrote", out, "pages:", n)
    return n


if __name__ == "__main__":
    build(sys.argv[1], int(sys.argv[2]))
