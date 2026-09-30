"""Data helpers shared by the Panel app, the Lite export and the notebook.

Nothing here changes a published number. The Government view reads
outputs/public/numbers.json. The Explorer view recomputes replays and
single-relay knockouts live with the functions in network.py and readouts.py.
"""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd
import yaml

from . import hazards, network as nw, readouts as ro
from .config import P, PROCESSED, PUBLIC, RESTRICTED, ROOT

MIN_PLACES = P["privacy"]["min_places"]
MIN_PEOPLE = P["privacy"]["min_people"]
BASELINE_DATE = "29 Sep 2026"
MONTHS = {"January (wet season)": 1, "July (dry season)": 7}
TRACKS = {"Whole system track": False, "Gale-strength part only": True}

# The 000 text is fixed. It is not generated per place.
TEXT_000 = ("In an emergency, call 000 from any mobile phone. The call can go over any "
            "network in range, not only your own. If there is no signal, use the free "
            "payphone. You cannot send a text message to 000.")
WATERMARK = "Illustrative sample. Not reviewed by any community."


def suppress(n, floor: int):
    """Counts between 1 and floor-1 are shown as '<floor'."""
    return f"<{floor}" if 0 < n < floor else int(n)


def numbers() -> dict:
    return json.loads((PUBLIC / "numbers.json").read_text())


@lru_cache(maxsize=1)
def base():
    """Graph and classified places, built the same way as pipeline.base_run()."""
    net = nw.load()
    places = pd.read_csv(PROCESSED / "places.csv")
    places = nw.assign_end_sites(places, net)
    c = nw.classify(places, net)
    return net, c


@lru_cache(maxsize=1)
def tracks() -> pd.DataFrame:
    return hazards.load_tracks()


@lru_cache(maxsize=1)
def power() -> pd.Series:
    net, _ = base()
    return ro.power_classes(net)


# ---------------------------------------------------------------------------
# Explorer: hazard replay, aggregated and suppressed
# ---------------------------------------------------------------------------
def replay_view(event_id: str, radius_km: int, cyclone_only: bool) -> dict:
    """Re-run one replay and return only aggregate, suppressed counts."""
    net, c = base()
    R = ro.replay(c, net, tracks(), event_id, radius_km, cyclone_only)
    L = R[R.larger & R.exposed]
    by_region = L.groupby("land_council").size()
    return {
        "footprint_relays": int(R.footprint_relays.iloc[0]),
        "exposed_larger": int(len(L)),
        "direct_larger": int(L.direct.sum()),
        "upstream_only_larger": int(L.upstream_only.sum()),
        "people_exposed_larger": suppress(int(L.population_2020.fillna(0).sum()), MIN_PEOPLE),
        "by_region": {k: suppress(int(v), MIN_PLACES) for k, v in by_region.items()},
    }


# ---------------------------------------------------------------------------
# Explorer: knock out one relay (restricted view)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def relay_register() -> pd.DataFrame:
    """Relays that are single points of failure, most depended-on first."""
    reg = pd.read_csv(RESTRICTED / "relay_register.csv")
    return reg.sort_values(["places", "larger_places", "site_key"], ascending=[False, False, True]).reset_index(drop=True)


def knockout(site_key: str, month: int) -> dict:
    """Remove one relay, re-trace every place, and report what loses its path."""
    net, c = base()
    cols = ["place_key", "name", "larger", "lat", "lon", "end_site", "population_2020", "land_council"]
    after = nw.classify(c[cols], net, removed={site_key})
    was_chain = c.chain_class.values == "radio-chain"
    lost = was_chain & after.chain_class.isin(["cut", "radio-island"]).values
    s = net.sites.loc[site_key]
    rep = ro.repair_days(s.lat, s.lon, s.dist_sealed_km, month)
    return {
        "places_lost": int(lost.sum()),
        "larger_lost": int((lost & c.larger.values).sum()),
        "people_lost_larger": suppress(int(c[lost & c.larger.values].population_2020.fillna(0).sum()), MIN_PEOPLE),
        "repair": rep,
        "band": ro.band(rep["total"]),
        "power_class": power().get(site_key, "P0_unknown"),
    }


# ---------------------------------------------------------------------------
# Government: KPI tiles, all read from numbers.json
# ---------------------------------------------------------------------------
def kpis(N: dict | None = None) -> list[dict]:
    N = N or numbers()
    ch, rl, rp, cf, pl = N["chains"], N["relays"], N["repair"], N["coverage_flags"], N["places"]
    no_backup = rl["spof_relays"] - rl["published_autonomy"]
    return [
        {"title": "Larger places that depend on 3 or more relays with no alternative path",
         "value": ch["with_ge3_spof"], "of": ch["radio_chain_places"], "unit": "larger radio-chain places",
         "target": "Halve by 2028 by adding a second path or backup to the shared relays",
         "owner": "DCDD with carriers", "refresh": "Monthly, with the ACMA radio licence register"},
        {"title": "Single-point relays with no published backup-power upgrade",
         "value": no_backup, "of": rl["spof_relays"], "unit": "single-point relays",
         "target": "Backup hours published for every single-point relay by 2027",
         "owner": "Carriers, reported to DCDD", "refresh": "Quarterly, with Mobile Network Hardening Program updates"},
        {"title": "Larger radio-chain places whose wet-season repair window is over 14 days",
         "value": rp["jan_bands"].get(">14 d", 0), "of": rp["radio_chain_places"], "unit": "larger radio-chain places",
         "target": "Pre-positioned spares or backup for each of these before the wet season",
         "owner": "DCDD with carriers and NTES", "refresh": "Yearly, before November"},
        {"title": "Places in the NTG 2021 register with no recorded mobile status",
         "value": cf["register_not_recorded"], "of": pl["all"], "unit": "places",
         "target": "Every place has a recorded status, checked each year",
         "owner": "DCDD", "refresh": "Yearly register update"},
    ]


def region_classes() -> pd.DataFrame:
    return pd.read_csv(PUBLIC / "region_classes.csv")


def replay_summary() -> pd.DataFrame:
    return pd.read_csv(PUBLIC / "replay_summary.csv")


# ---------------------------------------------------------------------------
# Community sample: rules table from config/rules.yaml, if present
# ---------------------------------------------------------------------------
def load_rules() -> dict | None:
    path = ROOT / "config" / "rules.yaml"
    return (yaml.safe_load(path.read_text()) or {}) if path.exists() else None


def text_000() -> str:
    """The fixed 000 wording: from rules.yaml when present, else our default."""
    R = load_rules() or {}
    return " ".join(str(R.get("triple_zero_text", TEXT_000)).split())


def rules_table() -> pd.DataFrame | None:
    """Services x outage scenarios from config/rules.yaml, or None if absent."""
    R = load_rules()
    if R is None:
        return None
    scen = R.get("scenarios", {})
    rows = []
    for svc in R.get("services", []):
        row = {"Service": svc.get("label", svc.get("id", ""))}
        for sid, rule in svc.get("rules", {}).items():
            # The printed word is the optional label, else the status.
            row[sid] = rule.get("label", rule.get("status", "")) if isinstance(rule, dict) else str(rule)
        rows.append(row)
    df = pd.DataFrame(rows)
    # Short column headings; the full scenario text is shown under the table.
    heads = {"normal_day": "Normal day", "tower_or_line_down": "Tower or line down",
             "community_power_down": "Community power down", "road_cut": "Road cut"}
    return df.rename(columns={k: heads.get(k, k) for k in scen} | heads)


# ---------------------------------------------------------------------------
# Government view: built once here so the app and the Lite file match
# ---------------------------------------------------------------------------
BLUE, ORANGE = "#2a78d6", "#eb6834"
CSS = """
.ul-tile {border:1px solid #d0d4da; border-radius:6px; padding:12px 14px; background:#fff; color:#1d232b;
          font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; width:100%; box-sizing:border-box;}
.ul-tile h4 {margin:0 0 6px 0; font-size:14px; font-weight:600; line-height:1.3;}
.ul-tile .v {font-size:30px; font-weight:700; color:#2a78d6;}
.ul-tile .of {font-size:13px; color:#4a525c;}
.ul-tile dl {margin:8px 0 0 0; font-size:12.5px; display:grid; grid-template-columns:auto 1fr; gap:3px 8px;}
.ul-tile dt {color:#5b636d;} .ul-tile dd {margin:0;}
.ul-note {font-size:13px; color:#3b434c; font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;}
.ul-restricted {background:#fdf0e9; border-left:4px solid #eb6834; padding:8px 12px;}
.ul-watermark {background:#f1f3f5; border:1px dashed #8a929b; padding:8px 12px; font-weight:600;}
.ul-card {max-width:760px;}
.ul-card table {border-collapse:collapse; font-size:14px;}
.ul-card td, .ul-card th {border:1px solid #d0d4da; padding:5px 9px; text-align:left;}
table.dataframe td, table.dataframe th {text-align:left !important;}
"""


def tile_html(k: dict) -> str:
    return (f"<div class='ul-tile'><h4>{k['title']}</h4>"
            f"<div><span class='v'>{k['value']}</span> <span class='of'>of {k['of']} {k['unit']}</span></div>"
            f"<dl><dt>Baseline</dt><dd>{k['value']} of {k['of']}, as at {BASELINE_DATE}</dd>"
            f"<dt>Proposed target</dt><dd>{k['target']}</dd>"
            f"<dt>Owner</dt><dd>{k['owner']}</dd><dt>Refresh</dt><dd>{k['refresh']}</dd></dl></div>")


def replay_chart():
    """Stacked bars: larger places exposed in each replay, split by cause."""
    from bokeh.models import ColumnDataSource
    from bokeh.plotting import figure
    rs = replay_summary()
    m = rs[(rs.radius_km == P["hazards"]["replay_radius_km"]) & (~rs.cyclone_only)].copy()
    m["direct"] = m.exposed_larger - m.upstream_only_larger
    src = ColumnDataSource(dict(event=list(m.event), direct=list(m.direct), upstream=list(m.upstream_only_larger)))
    f = figure(x_range=list(m.event), height=300, sizing_mode="stretch_width", toolbar_location=None,
               title=f"Larger radio-chain places that lose their path, {P['hazards']['replay_radius_km']} km footprint, whole track")
    f.vbar_stack(["direct", "upstream"], x="event", width=0.6, color=[BLUE, ORANGE], source=src,
                 legend_label=["Own site or place in footprint", "Cut off by an upstream relay only"])
    f.y_range.start = 0
    f.y_range.end = int(m.exposed_larger.max()) + 3   # room for the legend
    f.yaxis.axis_label = "Larger places"
    f.xgrid.grid_line_color = None
    f.legend.location = "top_right"
    f.legend.label_text_font_size = "11px"
    f.title.text_font_size = "13px"
    return f


def government_view():
    """KPI tiles, region table and replay chart. Public: aggregates only."""
    import panel as pn
    N = numbers()
    # one HTML block with its own grid: two tiles per row, one per row on phones
    tiles = pn.pane.HTML("<style>.ul-tiles{display:grid;grid-template-columns:1fr 1fr;gap:10px}"
                         "@media (max-width:720px){.ul-tiles{grid-template-columns:1fr}}</style>"
                         "<div class='ul-tiles'>" + "".join(tile_html(k) for k in kpis(N)) + "</div>",
                         sizing_mode="stretch_width")
    plain = {"land_council": "Land council region", "at-anchor": "At a fibre town", "radio-chain": "On a radio chain",
             "radio-island": "Radio island", "no-radio-site": "No licensed radio site nearby"}
    reg = region_classes().rename(columns=plain)[list(plain.values())]
    return pn.Column(
        pn.pane.HTML(f"<div class='ul-note'>Four measures DCDD could track. Baselines are as at {BASELINE_DATE} "
                     "and come from outputs/public/numbers.json. Targets are our proposals, not agreed policy. "
                     "Larger places are the 116 NTG towns, major and minor communities and villages.</div>",
                     sizing_mode="stretch_width"),
        tiles,
        pn.pane.Markdown("### Larger places by chain class and land council region"),
        pn.pane.DataFrame(reg, index=False, sizing_mode="stretch_width"),
        pn.pane.HTML("<div class='ul-note'>Each number is a count of larger places. <b>&lt;3</b> means 1 or 2 places: "
                     "we do not show exact small counts, so no single community can be picked out. "
                     "<b>At a fibre town</b>: its phone site is next to the fibre cable. <b>On a radio chain</b>: it reaches "
                     "the fibre cable through a line of radio relays. <b>Radio island</b>: it has radio links, but none we "
                     "can see reach fibre (probably satellite). <b>No licensed radio site nearby</b>: no licensed radio "
                     "site within 10 km.</div>"),
        pn.pane.Markdown("### Cyclone replays"),
        pn.pane.Bokeh(replay_chart(), sizing_mode="stretch_width"),
        pn.pane.HTML("<div class='ul-note'>A replay removes every relay near a past storm track and re-traces each "
                     "place. It shows exposure, not what happened in that storm.</div>"),
        sizing_mode="stretch_width", max_width=1000,
    )
