"""Export the Underlink results as a small star schema for a data warehouse.

    python -m underlink.schema      # writes outputs/restricted/warehouse/*.csv

The tables match docs/schema.sql and are described in docs/data_dictionary.md.
They sit in the restricted tier because dim_site and fact_chain_member carry
the hashed relay keys. No table holds a community name or a coordinate.

Dimensions carry valid_from / valid_to so a later snapshot (a new ACMA
register, a new community list) can be added as new rows, not overwrites.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from . import hazards, network as nw, readouts as ro
from .config import P, PROCESSED, RESTRICTED

WAREHOUSE = RESTRICTED / "warehouse"
SNAPSHOT = "2026-09-29"      # date of the data pull behind this run
VARIANT = "V1"               # V1: fibre-connected sites are treated as sound

# Load order matters for foreign keys: dimensions first, then facts.
TABLES = ["dim_place", "dim_site", "dim_event", "fact_place_snapshot", "fact_chain_member",
          "fact_replay_result", "fact_fallback", "fact_outage_event"]


def _base():
    """The same base run as pipeline.run(): default radii from params.yaml."""
    net = nw.load()
    places = pd.read_csv(PROCESSED / "places.csv")
    places = nw.assign_end_sites(places, net)
    return net, nw.classify(places, net)


def dim_place(c: pd.DataFrame) -> pd.DataFrame:
    # Names and coordinates are left out on purpose; place_key is the only link back.
    d = c[["place_key", "ntg_type", "larger", "land_council", "population_2020",
           "claimed_4g_2026", "mobile_2021"]].copy()
    d["population_2020"] = d.population_2020.round().astype("Int64")
    return d.assign(valid_from=SNAPSHOT, valid_to=None)


def dim_site(net: nw.Network) -> pd.DataFrame:
    power = ro.power_classes(net)
    s = net.sites.reset_index(drop=True)[["site_key", "dist_sealed_km"]].copy()
    s["power_class"] = s.site_key.map(power)
    s["is_fibre_connected"] = s.site_key.isin(net.roots)
    return s.assign(valid_from=SNAPSHOT, valid_to=None)


def dim_event() -> pd.DataFrame:
    ev = P["hazards"]["replay_events"]
    return pd.DataFrame({"event_key": [f"E{i + 1:02d}" for i in range(len(ev))],
                         "bom_disturbance_id": list(ev.keys()), "label": list(ev.values())})


def fact_place_snapshot(c: pd.DataFrame) -> pd.DataFrame:
    """One row per place: chain class, hops and SPOF count for this snapshot."""
    f = c[["place_key", "chain_class", "hops", "n_spof"]].copy()
    f["hops"] = f.hops.astype("Int64")
    return f.assign(variant=VARIANT, snapshot_date=SNAPSHOT)


def fact_chain_member(c: pd.DataFrame, net: nw.Network) -> pd.DataFrame:
    """Every site on one shortest radio path from a place's site to fibre.

    position 0 is the place's own site; the last position is the fibre-connected
    site. is_spof marks the relays with no alternative path (the dominators).
    Every dominator lies on every path, so all of them appear on this one.
    """
    H = nx.Graph(net.G)
    H.add_edges_from((nw.SOURCE, r) for r in net.roots)
    rows = []
    for r in c[c.chain_class == "radio-chain"].itertuples():
        path = nx.shortest_path(H, r.end_site, nw.SOURCE)[:-1]   # drop the fibre super-source
        spof = set(r.spof_relays)
        assert spof <= set(path), f"dominator missing from path for {r.place_key}"
        for pos, site in enumerate(path):
            role = "end_site" if pos == 0 else "fibre_site" if site in net.roots else "relay"
            rows.append({"place_key": r.place_key, "site_key": site, "position": pos, "role": role,
                         "is_spof": site in spof})
    return pd.DataFrame(rows).assign(variant=VARIANT, snapshot_date=SNAPSHOT)


def fact_replay_result(c: pd.DataFrame, net: nw.Network, events: pd.DataFrame) -> pd.DataFrame:
    """Status of every place under every replay: event x radius x track variant."""
    tracks = hazards.load_tracks()
    out = []
    for e in events.itertuples():
        for r_km in P["hazards"]["replay_radius_sweep_km"]:
            for cyc_only in (False, True):
                R = ro.replay(c, net, tracks, e.bom_disturbance_id, r_km, cyc_only)
                status = np.where(R.direct, "direct", np.where(R.upstream_only, "upstream_only", "not_affected"))
                out.append(pd.DataFrame({"event_key": e.event_key, "radius_km": r_km,
                                         "track_variant": "cyclone_only" if cyc_only else "system",
                                         "place_key": R.place_key.values, "status": status}))
    return pd.concat(out, ignore_index=True)


def fact_fallback(c: pd.DataFrame) -> pd.DataFrame:
    """Long form of readouts.fallbacks(): one row per place and channel type."""
    fb = ro.fallbacks(c)
    indep = pd.read_csv(PROCESSED / "fallbacks.csv").drop_duplicates("kind").set_index("kind").independence
    walk, oc = P["fallbacks"]["walk_radius_km"], P["fallbacks"]["other_carrier_radius_km"]
    kinds = [k for k in fb.columns if k not in ("place_key", "independent_fallback")]
    long = fb.melt(id_vars="place_key", value_vars=kinds, var_name="channel_type", value_name="count_within_km")
    long["radius_km"] = np.where(long.channel_type == "other_carrier_site", oc, walk)
    long["independence"] = long.channel_type.map(indep).fillna("separate network: other carrier")
    return long[["place_key", "channel_type", "count_within_km", "radius_km", "independence"]]


def fact_outage_event() -> pd.DataFrame:
    o = pd.read_csv(PROCESSED / "outage_ledger.csv")
    return pd.DataFrame({
        "outage_key": [f"O{i + 1:03d}" for i in range(len(o))],
        "source": o.source, "title": o.title,
        # the nbn register writes dates as dd/mm/yyyy; store ISO dates
        "start_date": pd.to_datetime(o.start, dayfirst=True).dt.date.astype(str),
        "end_date": pd.to_datetime(o.end, dayfirst=True).dt.date.astype(str),
        "duration_hours": o.duration, "states": o.states, "cause": o.cause, "nt_only": o.nt_only,
    })


def build() -> dict[str, pd.DataFrame]:
    net, c = _base()
    events = dim_event()
    return {
        "dim_place": dim_place(c),
        "dim_site": dim_site(net),
        "dim_event": events,
        "fact_place_snapshot": fact_place_snapshot(c),
        "fact_chain_member": fact_chain_member(c, net),
        "fact_replay_result": fact_replay_result(c, net, events),
        "fact_fallback": fact_fallback(c),
        "fact_outage_event": fact_outage_event(),
    }


def export() -> dict[str, int]:
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, df in build().items():
        df.to_csv(WAREHOUSE / f"{name}.csv", index=False)
        counts[name] = int(len(df))
    return counts


if __name__ == "__main__":
    for name, n in export().items():
        print(f"{name:22s} {n:>6d} rows")
    print(f"written to {WAREHOUSE}")
