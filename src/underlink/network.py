"""The licensed radio backhaul graph and each place's dependency chain.

Key idea: a community's mobile site reaches the wider network either over fibre
or over a chain of point-to-point radio relays licensed with ACMA. If every
path from the community's site back to fibre passes through one relay, that
relay is a single point of failure for the community. Graph theory calls the
set of such relays the *dominators* of the site, taken from a source joined to
all fibre-connected sites.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd

from .config import P, PROCESSED
from .geo import haversine_km

SOURCE = "__FIBRE__"   # super-source joined to every fibre-connected radio site


@dataclass
class Network:
    G: nx.Graph                      # undirected radio graph, nodes = hashed site keys
    sites: pd.DataFrame              # site_key, lat, lon, dist_sealed_km
    anchors: pd.DataFrame            # fibre towns
    roots: set = field(default_factory=set)            # radio sites treated as fibre-connected
    root_anchor: dict = field(default_factory=dict)    # root site -> set of anchor keys


def load(anchor_radius_km: float | None = None) -> Network:
    """Build the graph from data/processed and attach fibre anchors."""
    sites = pd.read_csv(PROCESSED / "sites.csv")
    links = pd.read_csv(PROCESSED / "links.csv")
    anchors = pd.read_csv(PROCESSED / "anchors.csv")
    G = nx.Graph()
    G.add_nodes_from(sites.site_key)
    for r in links.itertuples():
        G.add_edge(r.site_a, r.site_b, first_auth_year=r.first_auth_year, km=r.km)
    net = Network(G=G, sites=sites.set_index("site_key", drop=False), anchors=anchors)
    attach_anchors(net, anchor_radius_km or P["network"]["anchor_radius_km"])
    return net


def attach_anchors(net: Network, radius_km: float) -> None:
    """A radio site within radius_km of a fibre town counts as fibre-connected (a root)."""
    net.roots, net.root_anchor = set(), {}
    lat, lon = net.sites.lat.values, net.sites.lon.values
    keys = net.sites.site_key.values
    for a in net.anchors.itertuples():
        near = keys[haversine_km(a.lat, a.lon, lat, lon) <= radius_km]
        for k in near:
            net.roots.add(k)
            net.root_anchor.setdefault(k, set()).add(a.anchor_key)


def integrity(net: Network) -> dict:
    """Counts asserted in tests. Cycle rank = E - V + C (independent loops).

    We report it twice: on the radio graph alone, and with every fibre-connected
    site joined to one fibre source. Fibre closes some radio chains into loops,
    and the second number shows how much.
    """
    G = net.G
    V, E, C = G.number_of_nodes(), G.number_of_edges(), nx.number_connected_components(G)
    H = G.copy()
    H.add_edges_from((SOURCE, r) for r in net.roots)
    V2, E2, C2 = H.number_of_nodes(), H.number_of_edges(), nx.number_connected_components(H)
    return {"V": V, "E": E, "C": C, "cycle_rank_radio": E - V + C,
            "cycle_rank_with_fibre": E2 - V2 + C2, "roots": len(net.roots),
            "anchors": int(len(net.anchors)),
            "components_with_root": sum(1 for c in nx.connected_components(G) if c & net.roots)}


def dominator_tree(net: Network, removed: set | None = None) -> dict:
    """Immediate dominators from the fibre source, optionally with some sites removed."""
    D = net.G.to_directed()
    if removed:
        D.remove_nodes_from(removed)
    D.add_edges_from((SOURCE, r) for r in net.roots if r in D)
    return nx.immediate_dominators(D, SOURCE)


def chain_of(site: str, idom: dict, roots: set) -> list:
    """Relays with no alternative path between `site` and fibre (roots excluded).

    Walk up the dominator tree from the site to the fibre source. Every node on
    that walk lies on every path, so losing it cuts the site off.
    """
    out, v = [], idom.get(site)
    while v is not None and v != SOURCE:
        if v not in roots:
            out.append(v)
        nxt = idom.get(v)
        v = None if nxt == v else nxt
    return out


def assign_end_sites(places: pd.DataFrame, net: Network, radius_km: float | None = None) -> pd.DataFrame:
    """Nearest licensed radio site within radius_km stands in for the serving site."""
    radius_km = radius_km or P["network"]["end_site_radius_km"]
    lat, lon = net.sites.lat.values, net.sites.lon.values
    keys = net.sites.site_key.values
    ends, dists = [], []
    for r in places.itertuples():
        d = haversine_km(r.lat, r.lon, lat, lon)
        i = int(np.argmin(d))
        ends.append(keys[i] if d[i] <= radius_km else None)
        dists.append(round(float(d[i]), 2))
    return places.assign(end_site=ends, end_site_km=dists)


def classify(places: pd.DataFrame, net: Network, removed: set | None = None) -> pd.DataFrame:
    """Chain class, hops to fibre and single points of failure for every place.

    Classes:
      at-anchor      the end site is itself fibre-connected
      radio-chain    reaches fibre over one or more radio relays
      radio-island   has licensed radio links but no radio path to fibre
                     (probably satellite or unlicensed/fibre backhaul we cannot see)
      no-radio-site  no licensed point-to-point site within the search radius
    """
    idom = dominator_tree(net, removed)
    dist = nx.single_source_shortest_path_length(
        nx.Graph(list(net.G.edges()) + [(SOURCE, r) for r in net.roots]), SOURCE) if net.roots else {}
    rows = []
    for r in places.itertuples():
        e = r.end_site
        if e is None or (isinstance(e, float) and np.isnan(e)):
            rows.append(("no-radio-site", np.nan, [], np.nan)); continue
        if removed and e in removed:
            rows.append(("cut", np.nan, [], np.nan)); continue
        if e in net.roots:
            rows.append(("at-anchor", 0, [], np.nan)); continue
        if e not in idom:
            rows.append(("radio-island", np.nan, [], np.nan)); continue
        chain = chain_of(e, idom, net.roots)
        hops = dist.get(e, np.nan) - 1 if e in dist else np.nan
        # Earliest licence date on the chain is kept for provider use only; it is
        # a licence date, not equipment age, and we do not report it publicly.
        rows.append(("radio-chain", hops, chain, np.nan))
    out = places.copy()
    out["chain_class"] = [x[0] for x in rows]
    out["hops"] = [x[1] for x in rows]
    out["spof_relays"] = [x[2] for x in rows]
    out["n_spof"] = [len(x[2]) for x in rows]
    return out


def single_anchor_dependence(places: pd.DataFrame, net: Network) -> pd.DataFrame:
    """Fibre what-if: which places depend on one fibre town only?

    We add each fibre town as its own node between the source and its radio
    sites. If one town dominates a place's site, the place has no licensed
    radio path to any other fibre town, so a break in that town's fibre (as in
    Wadeye, 2026) would take the place down with it.
    """
    D = net.G.to_directed()
    for root, anchors in net.root_anchor.items():
        for a in anchors:
            D.add_edge(SOURCE, a)
            D.add_edge(a, root)
    idom = nx.immediate_dominators(D, SOURCE)
    anchor_keys = set(net.anchors.anchor_key)
    names = dict(zip(net.anchors.anchor_key, net.anchors.name))
    single = []
    for r in places.itertuples():
        e = r.end_site
        if not isinstance(e, str) or e not in idom:
            single.append(None); continue
        v, found = e, None
        while v is not None and v != SOURCE:
            if v in anchor_keys:
                found = v; break
            nxt = idom.get(v)
            v = None if nxt == v else nxt
        single.append(names.get(found) if found else None)
    return places.assign(single_fibre_town=single)


def relay_table(classified: pd.DataFrame, net: Network) -> pd.DataFrame:
    """One row per relay that is a single point of failure for at least one place."""
    rows = {}
    for r in classified.itertuples():
        for v in r.spof_relays:
            d = rows.setdefault(v, {"site_key": v, "places": 0, "larger_places": 0, "people": 0.0})
            d["places"] += 1
            d["larger_places"] += int(r.larger)
            d["people"] += 0 if np.isnan(r.population_2020) else r.population_2020
    t = pd.DataFrame(rows.values())
    if t.empty:
        return t
    cols = [c for c in ("site_key", "lat", "lon", "dist_sealed_km", "on_alra_land") if c in net.sites.columns]
    return t.merge(net.sites[cols].reset_index(drop=True), on="site_key", how="left")
