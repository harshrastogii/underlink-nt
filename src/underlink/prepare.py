"""Build the small, shippable tables in data/processed from the raw downloads.

This is the only step that needs the 2.2 GB of raw files in data_probe/. Every
later step reads data/processed only, so a judge can rerun the analysis from the
submitted ZIP without the raw data.

Two protections are applied here, before anything is written:
  * radio site IDs from the ACMA register are replaced by salted hashes, and
  * all coordinates are rounded to 0.01 degrees (about 1 km).
The source register is public and updated daily; the point is that our processed
files are not a ready-made lookup table of weak relays.
"""
from __future__ import annotations

import hashlib
import json
import secrets

import geopandas as gpd
import numpy as np
import pandas as pd
from rapidfuzz import fuzz

from .config import P, PROCESSED, RAW, REFERENCE, RESTRICTED, ensure_dirs
from .geo import haversine_km

ROUND = P["geometry"]["coord_round_deg"]
ALBERS = P["geometry"]["crs_metric"]


def _r(x):
    """Round coordinates to the shipping precision."""
    return np.round(np.asarray(x, dtype=float) / ROUND) * ROUND


def _salt() -> str:
    """A per-machine salt, kept in outputs/restricted (never shipped)."""
    path = RESTRICTED / "site_salt.txt"
    if not path.exists():
        path.write_text(secrets.token_hex(16))
    return path.read_text().strip()


def _key(site_id, salt: str) -> str:
    return "R" + hashlib.sha1(f"{salt}:{int(site_id)}".encode()).hexdigest()[:8]


# --------------------------------------------------------------------------
# 1. Place spine: the 782 places in the NTG 2021 register
# --------------------------------------------------------------------------
def build_places() -> pd.DataFrame:
    base = pd.read_csv(RAW / "listed-datasets/accc/nt_communities_telstra4g_outdoor_2026.csv")
    nbn = pd.read_csv(RAW / "listed-datasets/nbn/nt_communities_nbn_footprint.csv")
    base = base.merge(
        nbn[["COMMUNITY_NAME", "LONGITUDE", "LATITUDE", "fixed line", "fixed wireless"]],
        on=["COMMUNITY_NAME", "LONGITUDE", "LATITUDE"], how="left")
    places = pd.DataFrame({
        "place_key": [f"P{i:04d}" for i in range(len(base))],
        "name": base.COMMUNITY_NAME.str.title(),
        "ntg_type": base.COMMUNITY_TYPE,
        "larger": base.COMMUNITY_TYPE.isin(P["places"]["larger_types"]),
        "lat_full": base.LATITUDE, "lon_full": base.LONGITUDE,
        "mobile_2021": base.MOBILE_PHONE,               # NTG register field: Y / N / Not recorded
        "claimed_4g_2026": base.covered.astype(bool),    # inside Telstra 4G outdoor prediction (ACCC 2026 KML)
        "nbn_fixed_line": base["fixed line"].fillna(False).astype(bool),
        "nbn_fixed_wireless": base["fixed wireless"].fillna(False).astype(bool),
    })

    # Population: nearest Bushfires NT 2020 point, accepted if the names agree
    # (token-sort ratio >= 80 within 5 km) or it is very close (<= 1 km).
    bf = pd.read_csv(RAW / "nt-context-data/nt_remote_communities_bushfire_risk_2020.csv")
    pops, methods = [], []
    for r in places.itertuples():
        d = haversine_km(r.lat_full, r.lon_full, bf.LATITUDE.values, bf.LONGITUDE.values)
        i = int(np.argmin(d))
        score = fuzz.token_sort_ratio(str(r.name).upper(), str(bf.COMMUNITY.iloc[i]).upper())
        if (d[i] <= 5 and score >= 80) or d[i] <= 1:
            pops.append(bf.POPULATION.iloc[i]); methods.append("name+distance" if score >= 80 else "distance<=1km")
        else:
            pops.append(np.nan); methods.append("unmatched")
    places["population_2020"] = pops
    places["population_match"] = methods

    # Public aggregation units: land council region and Counter Disaster Area.
    pts = gpd.GeoDataFrame(places[["place_key"]], geometry=gpd.points_from_xy(places.lon_full, places.lat_full), crs="EPSG:4326")
    for layer, col in [("LAND_COUNCIL_BOUNDARIES", "land_council"), ("COUNTER_DISASTER_AREAS", "cda")]:
        poly = gpd.read_file(RAW / f"nt-context-data/ntlis_wfs/{layer}.geojson").to_crs("EPSG:4326")[["NAME", "geometry"]]
        j = gpd.sjoin(pts, poly, how="left", predicate="within").drop_duplicates("place_key")
        places[col] = j["NAME"].values
    places["land_council"] = places.land_council.fillna("Outside land council areas").str.title()

    # Unsealed share of road length within 25 km: our stand-in for wet-season access.
    roads = gpd.read_file(RAW / "nt-context-data/nt_national_roads_geoscape.geojson").to_crs(ALBERS)
    roads["len"] = roads.length
    roads["unsealed"] = roads["surface"].astype(str).str.upper().eq("UNSEALED")
    sidx = roads.sindex
    pts_m = pts.to_crs(ALBERS)
    buf = P["restore"]["unsealed_buffer_km"] * 1000
    share = []
    for g in pts_m.geometry:
        idx = sidx.query(g.buffer(buf))
        sub = roads.iloc[idx]
        sub = sub[sub.distance(g) <= buf]
        tot = sub.len.sum()
        share.append(float(sub.loc[sub.unsealed, "len"].sum() / tot) if tot > 0 else np.nan)
    places["unsealed_share_25km"] = share
    places["dist_sealed_km"] = dist_to_sealed(places.lat_full, places.lon_full, roads)

    places["lat"], places["lon"] = _r(places.lat_full), _r(places.lon_full)
    return places


def dist_to_sealed(lats, lons, roads=None) -> list:
    """Straight-line km from each point to the nearest sealed road segment.

    A place or relay far from any sealed road is the one a crew cannot reach
    once wet-season rain closes the dirt roads, so this drives the access term.
    """
    if roads is None:
        roads = gpd.read_file(RAW / "nt-context-data/nt_national_roads_geoscape.geojson").to_crs(ALBERS)
    sealed = roads[roads["surface"].astype(str).str.upper().eq("SEALED")]
    pts = gpd.GeoSeries(gpd.points_from_xy(lons, lats), crs="EPSG:4326").to_crs(ALBERS)
    idx = sealed.sindex.nearest(pts, return_all=False)
    return list(np.round(pts.iloc[idx[0]].reset_index(drop=True).distance(sealed.geometry.iloc[idx[1]].reset_index(drop=True)).values / 1000, 2))


# --------------------------------------------------------------------------
# 2. Telstra licensed point-to-point radio links (ACMA RRL)
# --------------------------------------------------------------------------
def build_network(salt: str):
    L = pd.read_csv(RAW / "listed-datasets/acma/nt_p2p_links.csv", low_memory=False)
    L = L[L.LICENCEE.str.contains(P["network"]["licensee_pattern"], case=False, na=False)].dropna(subset=["RX_SITE"])
    licensees = sorted(L.LICENCEE.unique())
    L["year"] = pd.to_datetime(L.AUTHORISATION_DATE, errors="coerce").dt.year
    edges, pos = {}, {}
    for r in L.itertuples():
        a, b = int(r.SITE_ID), int(r.RX_SITE)
        if a == b:
            continue
        pos[a] = (r.tx_lat, r.tx_lon)
        pos[b] = (r.rx_lat, r.rx_lon)
        k = tuple(sorted((a, b)))
        y = r.year if not np.isnan(r.year) else np.nan
        bw = float(r.BANDWIDTH) / 1e6 if not pd.isna(r.BANDWIDTH) else np.nan   # licensed channel width, MHz
        if k in edges:
            edges[k]["first_auth_year"] = np.nanmin([edges[k]["first_auth_year"], y])
            edges[k]["max_bw_mhz"] = np.nanmax([edges[k]["max_bw_mhz"], bw])
        else:
            edges[k] = {"first_auth_year": y, "km": r.km, "max_bw_mhz": bw}
    sites = pd.DataFrame([(s, *pos[s]) for s in pos], columns=["site_id", "lat_full", "lon_full"])
    sites["site_key"] = [_key(s, salt) for s in sites.site_id]
    sites["dist_sealed_km"] = dist_to_sealed(sites.lat_full, sites.lon_full)
    # Tenure flag only: a relay on an Aboriginal Land Trust needs a section 19 lease for new works.
    # It never changes any ordering; it tells a planner to start the consent pathway early.
    lt = gpd.read_file(RAW / "nt-context-data/ntlis_wfs/ABORIGINAL_LAND_TRUSTS.geojson").to_crs("EPSG:4326")[["geometry"]]
    pts = gpd.GeoDataFrame(sites[["site_id"]], geometry=gpd.points_from_xy(sites.lon_full, sites.lat_full), crs="EPSG:4326")
    j = gpd.sjoin(pts, lt, how="left", predicate="within")
    sites["on_alra_land"] = j.groupby(level=0).index_right.apply(lambda x: x.notna().any()).reindex(sites.index).values
    sites["lat"], sites["lon"] = _r(sites.lat_full), _r(sites.lon_full)
    keymap = dict(zip(sites.site_id, sites.site_key))
    links = pd.DataFrame([{"site_a": keymap[a], "site_b": keymap[b], **v} for (a, b), v in edges.items()])
    # The unhashed crosswalk stays in the restricted folder for provider conversations.
    sites[["site_key", "site_id", "lat_full", "lon_full"]].to_csv(RESTRICTED / "site_crosswalk.csv", index=False)
    meta = {"licensee_values": licensees, "p2p_rows": int(len(L))}
    return sites[["site_key", "lat", "lon", "dist_sealed_km", "on_alra_land", "lat_full", "lon_full"]], links, meta


# --------------------------------------------------------------------------
# 3. Fibre anchors: NTG 2019 "Optic fibre" places plus regional centres
# --------------------------------------------------------------------------
def build_anchors() -> pd.DataFrame:
    B = pd.read_excel(RAW / "listed-datasets/ntg/remote-communities-mobile-coverage-backhaul-2019.xlsx", header=1)
    B.columns = ["name", "lat", "lon", "backhaul", "provider"]
    B["lat"], B["lon"] = pd.to_numeric(B.lat, errors="coerce"), pd.to_numeric(B.lon, errors="coerce")
    fib = B[B.backhaul == "Optic fibre"].dropna(subset=["lat"])[["name", "lat", "lon"]].assign(kind="ntg_2019_optic_fibre")
    rc = pd.DataFrame([(k, v[0], v[1]) for k, v in P["network"]["regional_centres"].items()], columns=["name", "lat", "lon"]).assign(kind="regional_centre")
    a = pd.concat([fib, rc], ignore_index=True)
    a["anchor_key"] = [f"A{i:02d}" for i in range(len(a))]
    return a[["anchor_key", "name", "kind", "lat", "lon"]]


def build_backhaul_register() -> pd.DataFrame:
    """The NTG 2019 list, kept whole: its microwave entries are useful context."""
    B = pd.read_excel(RAW / "listed-datasets/ntg/remote-communities-mobile-coverage-backhaul-2019.xlsx", header=1)
    B.columns = ["name", "lat", "lon", "backhaul", "provider"]
    return B


# --------------------------------------------------------------------------
# 4. Cyclone tracks (BoM best track), every system with a fix near the NT
# --------------------------------------------------------------------------
def build_tracks() -> pd.DataFrame:
    T = pd.read_csv(RAW / "listed-datasets/cyclone/IDCKMSTM0S.csv", skiprows=4, low_memory=False)
    T["time"] = pd.to_datetime(T.TM, errors="coerce")
    T["lat"], T["lon"] = pd.to_numeric(T.LAT, errors="coerce"), pd.to_numeric(T.LON, errors="coerce")
    T["max_wind_ms"] = pd.to_numeric(T.MAX_WIND_SPD, errors="coerce")
    T = T.dropna(subset=["time", "lat", "lon"])
    y0, y1 = P["hazards"]["exposure_window"]
    near_nt = T[(T.lat.between(-27, -9)) & (T.lon.between(127, 140))].DISTURBANCE_ID.unique()
    T = T[T.DISTURBANCE_ID.isin(near_nt) & T.time.dt.year.between(y0, y1)]
    return T[["DISTURBANCE_ID", "NAME", "time", "lat", "lon", "max_wind_ms"]].rename(columns={"DISTURBANCE_ID": "event_id", "NAME": "event_name"}).sort_values(["event_id", "time"])


# --------------------------------------------------------------------------
# 5. Power: Mobile Network Hardening Program items
# --------------------------------------------------------------------------
def build_power() -> pd.DataFrame:
    M = pd.read_csv(RAW / "au-telecom-infra/mnhp/mnhp_nt_all_layers.csv")

    def cls(r):
        u = str(r.upgrade).lower()
        if "portable generator" in u or "depot" in u:
            return "P4_depot"
        if r.layer.startswith("MNHP R2"):
            return "P1_battery_12h_in_progress"
        if "permanent generator" in u:
            return "P2_permanent_generator"
        if "batter" in u:
            return "P3_battery_replacement"
        return "P3_other_upgrade"
    M["power_class"] = M.apply(cls, axis=1)
    M["lat"], M["lon"] = _r(M.lat), _r(M.lon)
    return M[["layer", "location", "grantee", "upgrade", "status", "power_class", "lat", "lon"]]


# --------------------------------------------------------------------------
# 6. Fallbacks, other carriers, already-funded work
# --------------------------------------------------------------------------
def build_fallbacks() -> pd.DataFrame:
    d = RAW / "au-telecom-infra/payphones"
    parts = [
        (pd.read_csv(d / "wifi_telephones_nt.csv"), "wifi_phone", "independent: satellite"),
        (pd.read_csv(d / "community_payphones_nt.csv"), "community_payphone", "unknown: ask locally"),
        (pd.read_csv(d / "payphones_ric_nt.csv"), "ric_payphone", "unknown: ask locally"),
        (pd.read_csv(d / "wifi_hubs_nt.csv"), "wifi_hub", "usually satellite: check"),
        (pd.read_csv(d / "community_wifi_nbn_nt.csv"), "community_wifi_nbn", "usually satellite: check"),
        (pd.read_csv(RAW / "au-telecom-infra/stand/stand_skymuster_nt.csv"), "stand_sky_muster", "independent: satellite"),
    ]
    out = []
    for df, kind, indep in parts:
        df = df.dropna(subset=["lat", "lon"])
        out.append(pd.DataFrame({"kind": kind, "independence": indep, "lat": _r(df.lat), "lon": _r(df.lon)}))
    return pd.concat(out, ignore_index=True)


def build_other_carriers() -> pd.DataFrame:
    A = pd.read_csv(RAW / "listed-datasets/accc/accc_mobile_sites_NT_bbox_2018_2026.csv", low_memory=False)
    A = A[(A.Year == 2026) & (A.MNO.str.lower() != "telstra")]
    return pd.DataFrame({"mno": A.MNO, "lat": _r(A.Latitude), "lon": _r(A.Longitude)})


def build_telstra_sites() -> pd.DataFrame:
    """Telstra mobile sites the ACCC lists for 2026. Used only to check that each radio chain ends at a mobile site."""
    A = pd.read_csv(RAW / "listed-datasets/accc/accc_mobile_sites_NT_bbox_2018_2026.csv", low_memory=False)
    A = A[(A.Year == 2026) & (A.MNO.str.lower() == "telstra")].dropna(subset=["Latitude", "Longitude"])
    # Co_funded marks sites built with government co-investment (the lever in Recommendation 1).
    cof = A.Co_funded.astype(str).str.strip().str.lower().isin(["y", "yes", "true", "1"])
    # The flag covers federal, state and local programs; only NT programs carry an NT condition.
    nt = cof & A.Co_contribution_program.astype(str).str.contains(r"\bNT\b|Northern Territory", regex=True)
    return pd.DataFrame({"lat": _r(A.Latitude), "lon": _r(A.Longitude), "co_funded": cof.values, "nt_program": nt.values})


def flood_1pc_km(lat, lon) -> "pd.Series":
    """Distance (km) from each point to the nearest published 1% AEP flood study area: the NT Planning Scheme
    'subject to flooding' overlay (NTLIS). Computed here on full coordinates and full polygons; only the
    distances are shipped, so no flood polygon or study name (several name a community) is in data/processed."""
    import geopandas as gpd
    g = gpd.read_file(RAW / "nt-context-data/ntlis_wfs/NTPS_SUBJECT_TO_FLOODING.geojson").to_crs(3577)
    flood = g.union_all()
    pts = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(3577)
    return (pts.distance(flood) / 1000).round(1).values


def build_funded() -> pd.DataFrame:
    rows = []
    # Mobile Black Spot Program: coordinates come from the KML extract, keyed by MBSP_ID.
    k = pd.read_csv(RAW / "au-telecom-infra/mbsp/mbsp_nt_kml_points.csv")
    k["lat"], k["lon"] = pd.to_numeric(k.lat, errors="coerce"), pd.to_numeric(k.lon, errors="coerce")
    k = k.dropna(subset=["lat", "lon"]).drop_duplicates("MBSP_ID")
    for r in k.itertuples():
        rows.append(("mbsp_" + str(r.Site_Status).lower().replace(" ", "_"), r.Location, r.lat, r.lon))
    # First Nations Community Wi-Fi Program 2026: located through AGIL codes.
    fn = pd.read_csv(RAW / "nt-connectivity-landscape/fn_wifi_funded_projects_2026.csv")
    fn = fn[fn.state == "NT"]
    agil = gpd.read_file(RAW / "listed-datasets/fnmap/nt_agil.geojson").drop_duplicates("code").set_index("code")
    for r in fn.itertuples():
        if r.agil_code in agil.index:
            rows.append((f"fn_wifi_2026_{'leo' if 'LEO' in str(r.technology) else 'geo'}", r.location,
                         float(agil.loc[r.agil_code, "latitude"]), float(agil.loc[r.agil_code, "longitude"])))
    f = pd.DataFrame(rows, columns=["kind", "location", "lat", "lon"])
    f["lat"], f["lon"] = _r(f.lat), _r(f.lon)
    return f


def build_outage_ledger() -> pd.DataFrame:
    O = pd.read_csv(RAW / "nt-connectivity-landscape/nbn_outage_register.csv")
    nt = O[O["Affected State(s)/Territories"].astype(str).str.contains("NT|Northern Territory", regex=True)]
    # The register's Duration is hours.minutes and sometimes drops the minutes' leading zero
    # (28.4 means 28 h 04 min), so hours are computed from the start and end times instead.
    ts = lambda d, t: pd.to_datetime(nt[d].astype(str) + " " + nt[t].astype(str).str.extract(r"(\d{1,2}:\d{2})")[0],
                                     format="%d/%m/%Y %H:%M")
    start, end = ts("Start date of outage", "Start time of outage"), ts("End date of outage", "End time of outage")
    return pd.DataFrame({
        "source": "nbn register", "reference": nt["Reference"],
        "title": nt["Outage title"], "start": start.dt.strftime("%Y-%m-%d %H:%M"), "end": end.dt.strftime("%Y-%m-%d %H:%M"),
        "duration_hours": ((end - start).dt.total_seconds() / 3600).round(2), "duration_published": nt["Duration of outage"],
        "states": nt["Affected State(s)/Territories"],
        "towns": nt["Affected suburb(s)/towns"], "cause": nt["Cause (high-level)"],
        "nt_only": nt["Affected State(s)/Territories"].astype(str).str.strip().isin(["NT", "Northern Territory"]),
    })


def build_namc() -> pd.DataFrame:
    N = pd.read_csv(RAW / "listed-datasets/fnmap/namc_nonalign_NT.csv")
    g = gpd.GeoSeries.from_wkt(N.WKT, crs="EPSG:4326").to_crs(ALBERS).centroid.to_crs("EPSG:4326")
    return pd.DataFrame({"mno": N.MNO, "audit": N["Audit Data"], "feedback": N["MNO Feedback on non-alignment"], "lat": _r(g.y), "lon": _r(g.x)})


def main() -> dict:
    ensure_dirs()
    salt = _salt()
    places = build_places()
    sites, links, meta = build_network(salt)
    anchors = build_anchors()
    places["flood_study_km"] = flood_1pc_km(places.lat_full, places.lon_full)
    sites["flood_1pc_km"] = flood_1pc_km(sites.lat_full, sites.lon_full)
    out = {
        "places": places.drop(columns=["lat_full", "lon_full"]),
        "sites": sites[["site_key", "lat", "lon", "dist_sealed_km", "on_alra_land", "flood_1pc_km"]],
        "links": links,
        "anchors": anchors,
        "tracks": build_tracks(),
        "power": build_power(),
        "fallbacks": build_fallbacks(),
        "other_carriers": build_other_carriers(),
        "telstra_mobile_sites": build_telstra_sites(),
        "funded": build_funded(),
        "outage_ledger": build_outage_ledger(),
        "namc_tiles": build_namc(),
        "ntg_backhaul_2019": build_backhaul_register(),
    }
    for name, df in out.items():
        df.to_csv(PROCESSED / f"{name}.csv", index=False)

    meta.update({name: int(len(df)) for name, df in out.items()})
    meta["population_match"] = places.population_match.value_counts().to_dict()
    (PROCESSED / "prepare_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, default=str))
