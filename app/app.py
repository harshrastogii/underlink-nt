"""Underlink app. Runs offline on this computer.

    panel serve app/app.py --port 5006

Three tabs:
  Explorer            restricted: replays and single-relay knockouts, recomputed live
  Government          public: KPI tiles, region table and replay chart
  Community (sample)  a synthetic "what still works" card
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import panel as pn  # noqa: E402

from underlink import app_data as A  # noqa: E402
from underlink.config import P  # noqa: E402

# Serve every JS and CSS file from this machine: no CDN, no web fonts.
pn.config.inline = True
pn.extension(raw_css=[A.CSS], inline=True, design=None, notifications=False)
pn.config.raw_css = [A.CSS]

EVENTS = {label: eid for eid, label in P["hazards"]["replay_events"].items()}


# ---------------------------------------------------------------------------
# Explorer (restricted)
# ---------------------------------------------------------------------------
w_event = pn.widgets.Select(name="Storm", options=list(EVENTS), value="Lam 2015")
w_radius = pn.widgets.RadioButtonGroup(name="Radius", options=[50, 100, 150], value=100)
w_track = pn.widgets.RadioButtonGroup(name="Track", options=list(A.TRACKS))
w_month = pn.widgets.RadioButtonGroup(name="Month", options=list(A.MONTHS))

# Relay choices, most depended-on first. Keys only; no coordinates.
REG = A.relay_register()
RELAY_OPTS = {f"#{i + 1}  {r.site_key}  ({r.places} places depend on it)": r.site_key
              for i, r in REG.iterrows()}
w_relay = pn.widgets.Select(name="Relay", options=RELAY_OPTS, width=380)


def _labelled(label: str, widget):
    # RadioButtonGroup shows no name, so add a small label above it.
    return pn.Column(pn.pane.HTML(f"<div class='ul-note'>{label}</div>", margin=(0, 10)), widget)


def _stat(label: str, value, colour: str = A.BLUE) -> str:
    return (f"<div class='ul-tile'><h4>{label}</h4>"
            f"<div class='v' style='color:{colour}'>{value}</div></div>")


@pn.depends(w_event, w_radius, w_track)
def replay_panel(event, radius, track):
    # Remove every relay near the track and re-trace all places.
    v = A.replay_view(EVENTS[event], radius, A.TRACKS[track])
    regions = "".join(f"<tr><td>{k}</td><td>{n}</td></tr>" for k, n in v["by_region"].items()) \
        or "<tr><td colspan=2>None</td></tr>"
    return pn.Column(
        pn.GridBox(
            pn.pane.HTML(_stat("Larger radio-chain places exposed", v["exposed_larger"])),
            pn.pane.HTML(_stat("Own site or place in footprint", v["direct_larger"])),
            pn.pane.HTML(_stat("Cut off by an upstream relay only", v["upstream_only_larger"], A.ORANGE)),
            pn.pane.HTML(_stat("People in exposed larger places", v["people_exposed_larger"])),
            ncols=4, sizing_mode="stretch_width"),
        pn.pane.HTML(f"<div class='ul-card ul-note'><p>{v['footprint_relays']} relays inside the footprint.</p>"
                     f"<table><tr><th>Land council region</th><th>Larger places exposed</th></tr>{regions}</table>"
                     "<p>Counts of 1 or 2 places show as &lt;3. People counts under 10 show as &lt;10.</p></div>"),
        sizing_mode="stretch_width")


@pn.depends(w_relay, w_month)
def knockout_panel(key, month_label):
    # Remove only this relay and see which places lose every path to fibre.
    k = A.knockout(key, A.MONTHS[month_label])
    r = k["repair"]
    return pn.Column(
        pn.GridBox(
            pn.pane.HTML(_stat("Places that lose their path", k["places_lost"])),
            pn.pane.HTML(_stat("Of which larger places", k["larger_lost"])),
            pn.pane.HTML(_stat("People in those larger places", k["people_lost_larger"])),
            pn.pane.HTML(_stat("Indicative repair window", f"{r['total']:.1f} d", A.ORANGE)),
            ncols=4, sizing_mode="stretch_width"),
        pn.pane.HTML(
            "<div class='ul-card ul-note'><table>"
            "<tr><th>Repair part</th><th>Days</th></tr>"
            f"<tr><td>Base (diagnose and fix on site)</td><td>{r['base']:.2f}</td></tr>"
            f"<tr><td>Travel from nearest depot</td><td>{r['travel']:.2f}</td></tr>"
            f"<tr><td>Wet-season access wait</td><td>{r['access']:.2f}</td></tr>"
            f"<tr><td><b>Total</b> ({k['band']})</td><td><b>{r['total']:.2f}</b></td></tr></table>"
            f"<p>Power class: <b>{k['power_class']}</b>. P0 means backup hours are not published, "
            "not that there is no battery. P4 means within 150 km of a portable-generator depot.</p>"
            "<p>Every repair input is an assumption in config/params.yaml. Read this as a split of "
            "where the time goes, not a prediction.</p></div>"),
        sizing_mode="stretch_width")


explorer = pn.Column(
    pn.pane.HTML("<div class='ul-note ul-restricted'><b>Restricted: relay detail, for DCDD and carriers.</b> "
                 "Relay keys are hashed. Do not share this view outside those agencies.</div>",
                 sizing_mode="stretch_width"),
    pn.pane.Markdown("### Replay a past storm"),
    pn.Row(w_event, _labelled("Radius (km)", w_radius), _labelled("Track", w_track)),
    replay_panel,
    pn.pane.Markdown("### Knock out one relay"),
    pn.Row(w_relay, _labelled("Month", w_month)),
    knockout_panel,
    sizing_mode="stretch_width", max_width=1000,
)


# ---------------------------------------------------------------------------
# Community (sample)
# ---------------------------------------------------------------------------
def community_view():
    rules = A.rules_table()
    parts = [
        pn.pane.HTML(f"<div class='ul-note ul-watermark'>{A.WATERMARK}</div>", sizing_mode="stretch_width"),
        pn.pane.Markdown("### Sample Community: what still works when the phone goes down"),
    ]
    if rules is None:
        parts.append(pn.pane.HTML("<div class='ul-note'>The rules file config/rules.yaml is not in this copy, "
                                  "so the table is not shown.</div>"))
    else:
        parts.append(pn.pane.DataFrame(rules, index=False, sizing_mode="stretch_width"))
        parts.append(pn.pane.HTML("<div class='ul-note'>'Ask locally' means we found no public source. "
                                  "Check with the clinic, store, council or school.</div>"))
    parts.append(pn.pane.HTML(f"<div class='ul-note ul-card'><h4>Triple Zero (000)</h4><p>{A.text_000()}</p></div>"))
    return pn.Column(*parts, sizing_mode="stretch_width", max_width=900)


tabs = pn.Tabs(
    ("Explorer (restricted)", explorer),
    ("Government", A.government_view()),
    ("Community (sample)", community_view()),
    dynamic=False, sizing_mode="stretch_width",
)

pn.Column(
    pn.pane.HTML("<div class='ul-note'><b style='font-size:18px'>Underlink</b> "
                 "Revealing the hidden dependencies behind NT connectivity</div>"),
    tabs, sizing_mode="stretch_width",
).servable(title="Underlink")
