"""The readouts that sit beside the chain analysis: hazard replay, power,
repair window and what still works. Each one is kept separate. Nothing here
is merged into a single score.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import hazards, network as nw
from .config import P, PROCESSED
from .geo import count_within, haversine_km


# --------------------------------------------------------------------------
# Hazard replay: exposure, never a claim about what happened
# --------------------------------------------------------------------------
def replay(classified: pd.DataFrame, net: nw.Network, tracks: pd.DataFrame,
           event_id: str, radius_km: float, cyclone_only: bool = False) -> pd.DataFrame:
    """Remove every relay within radius_km of the track and re-trace each place.

    A radio-chain place is *exposed* if it loses its path to fibre. It is
    *upstream-only* if neither the place nor its own site was near the track:
    the storm never reached it, but a relay it depends on was in the footprint.
    Fibre-connected sites are never removed (variant V1 treats fibre as sound).
    """
    fixes = tracks[tracks.event_id == event_id]
    geom = hazards.track_geometry(fixes, cyclone_only)
    site_pts = hazards.to_metric_points(net.sites.reset_index(drop=True))
    in_zone = hazards.within(site_pts, geom, radius_km)
    footprint = set(net.sites.site_key.values[in_zone.values]) - net.roots
    after = nw.classify(classified[["place_key", "name", "larger", "lat", "lon", "end_site", "population_2020", "land_council"]], net, removed=footprint)
    place_pts = hazards.to_metric_points(classified)
    place_near = hazards.within(place_pts, geom, radius_km).values
    base = classified.chain_class.values
    lost = (base == "radio-chain") & np.isin(after.chain_class.values, ["cut", "radio-island"])
    own_site_hit = classified.end_site.isin(footprint).values
    direct = lost & (own_site_hit | place_near)
    return classified.assign(exposed=lost, direct=direct, upstream_only=lost & ~direct,
                             event_id=event_id, radius_km=radius_km, cyclone_only=cyclone_only,
                             footprint_relays=len(footprint))


# --------------------------------------------------------------------------
# Power: published backup at relays, and everything we cannot see
# --------------------------------------------------------------------------
def power_classes(net: nw.Network) -> pd.Series:
    """P1-P3: a Mobile Network Hardening Program item within 3 km of the relay.
    P4: within 150 km of a Telstra portable-generator depot. P0: unknown.
    P0 means the battery hours are not published, not that there is no battery.
    """
    M = pd.read_csv(PROCESSED / "power.csv")
    k = P["power"]["mnhp_match_km"]
    items = M[M.power_class != "P4_depot"]
    depots = M[(M.power_class == "P4_depot")]
    out = {}
    for s in net.sites.itertuples():
        cls = "P0_unknown"
        if len(items):
            d = haversine_km(s.lat, s.lon, items.lat.values, items.lon.values)
            if d.min() <= k:
                cls = items.power_class.values[int(np.argmin(d))]
        if cls == "P0_unknown" and len(depots):
            if haversine_km(s.lat, s.lon, depots.lat.values, depots.lon.values).min() <= P["power"]["depot_radius_km"]:
                cls = "P4_depot_within_150km"
        out[s.site_key] = cls
    return pd.Series(out, name="power_class")


# --------------------------------------------------------------------------
# Repair window: base + travel + wet-season access, in days
# --------------------------------------------------------------------------
def repair_days(lat: float, lon: float, dist_sealed_km: float, month: int,
                w_wet: float | None = None, sealed_threshold: float | None = None) -> dict:
    """Indicative days to restore one relay, split into its parts.

    travel: nearest depot, straight-line x circuity at sealed speed, plus the
            last leg off the sealed network at unsealed speed.
    access: in wet-season months, a relay more than `sealed_threshold` km from
            any sealed road waits `w_wet` days for access to reopen.
    Every parameter is an assumption in params.yaml and is swept.
    """
    R = P["restore"]
    w_wet = R["w_wet_days"] if w_wet is None else w_wet
    sealed_threshold = R["wet_sealed_distance_km"] if sealed_threshold is None else sealed_threshold
    depots = np.array(list(R["depots"].values()))
    km = haversine_km(lat, lon, depots[:, 0], depots[:, 1]).min() * R["circuity"]
    off = max(dist_sealed_km, 0) * R["circuity"]
    hours = max(km - off, 0) / R["speed_sealed_kmh"] + off / R["speed_unsealed_kmh"]
    travel = hours / R["driving_hours_per_day"]
    access = w_wet if (month in R["wet_months"] and dist_sealed_km > sealed_threshold) else 0.0
    base = R["t_base_days"]
    return {"base": base, "travel": round(travel, 2), "access": access, "total": round(base + travel + access, 2)}


def band(days: float) -> str:
    b1, b2, b3 = P["restore"]["bands_days"]
    return "<1 d" if days < b1 else "1-3 d" if days < b2 else "3-14 d" if days < b3 else ">14 d"


def place_repair(classified: pd.DataFrame, net: nw.Network, month: int, **kw) -> pd.DataFrame:
    """For each radio-chain place, the slowest element on its chain sets its window."""
    rows = []
    for r in classified[classified.chain_class == "radio-chain"].itertuples():
        elems = list(r.spof_relays) + [r.end_site]
        parts = [repair_days(net.sites.loc[e, "lat"], net.sites.loc[e, "lon"], net.sites.loc[e, "dist_sealed_km"], month, **kw) for e in elems]
        worst = max(parts, key=lambda d: d["total"])
        rows.append({"place_key": r.place_key, "month": month, **worst, "band": band(worst["total"])})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# What still works: fallbacks within walking distance
# --------------------------------------------------------------------------
def fallbacks(places: pd.DataFrame) -> pd.DataFrame:
    F = pd.read_csv(PROCESSED / "fallbacks.csv")
    O = pd.read_csv(PROCESSED / "other_carriers.csv")
    walk = P["fallbacks"]["walk_radius_km"]
    oc = P["fallbacks"]["other_carrier_radius_km"]
    out = places[["place_key"]].copy()
    for kind, g in F.groupby("kind"):
        out[kind] = [count_within(r.lat, r.lon, g.lat.values, g.lon.values, walk) for r in places.itertuples()]
    out["other_carrier_site"] = [count_within(r.lat, r.lon, O.lat.values, O.lon.values, oc) for r in places.itertuples()]
    indep = [c for c in ("wifi_phone", "stand_sky_muster") if c in out]
    out["independent_fallback"] = out[indep].sum(axis=1) > 0
    return out


def funded_flags(places: pd.DataFrame) -> pd.DataFrame:
    Fd = pd.read_csv(PROCESSED / "funded.csv")
    out = places[["place_key"]].copy()
    for kind, km in (("mbsp_in_progress", 10), ("fn_wifi_2026_leo", 5), ("fn_wifi_2026_geo", 5)):
        g = Fd[Fd.kind == kind]
        out[kind] = [count_within(r.lat, r.lon, g.lat.values, g.lon.values, km) > 0 for r in places.itertuples()]
    return out
