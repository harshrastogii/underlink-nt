"""Run every readout from data/processed and write outputs + numbers.json.

numbers.json is the single source for every number quoted in the report, the
deck and the app. If a number is not in it, it does not go in print.
"""
from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd

from . import hazards, network as nw, readouts as ro
from .geo import haversine_km
from .config import P, PROCESSED, PUBLIC, RESTRICTED, ensure_dirs, public_region

MIN_PLACES = P["privacy"]["min_places"]
MIN_PEOPLE = P["privacy"]["min_people"]


def suppress(n: float, floor: int) -> float | str:
    """Public counts below the floor are shown as '<floor'."""
    return f"<{floor}" if 0 < n < floor else n


def base_run(anchor_km=None, end_km=None):
    net = nw.load(anchor_km)
    places = pd.read_csv(PROCESSED / "places.csv")
    places = nw.assign_end_sites(places, net, end_km)
    c = nw.classify(places, net)
    return net, c


def run() -> dict:
    ensure_dirs()
    N: dict = {}
    net, c = base_run()
    c = nw.single_anchor_dependence(c, net)
    L = c[c.larger]
    rc = L[L.chain_class == "radio-chain"]

    # --- 1. Network integrity and chain classes --------------------------------
    N["network"] = nw.integrity(net)
    N["places"] = {
        "all": int(len(c)), "larger": int(len(L)),
        "larger_with_radio_site": int(L.end_site.notna().sum()),
        "larger_classes": L.chain_class.value_counts().to_dict(),
        "all_classes": c.chain_class.value_counts().to_dict(),
        "population_match": c.population_match.value_counts().to_dict(),
    }
    N["chains"] = {
        "radio_chain_places": int(len(rc)),
        "hops_median": float(rc.hops.median()), "hops_max": float(rc.hops.max()),
        "with_ge1_spof": int((rc.n_spof >= 1).sum()), "with_ge3_spof": int((rc.n_spof >= 3).sum()),
        "people_on_radio_chains": int(rc.population_2020.sum()),
        "people_ge1_spof": int(rc[rc.n_spof >= 1].population_2020.sum()),
        "people_ge3_spof": int(rc[rc.n_spof >= 3].population_2020.sum()),
        "all_places_radio_chain": int((c.chain_class == "radio-chain").sum()),
        "all_places_ge1_spof": int(((c.chain_class == "radio-chain") & (c.n_spof >= 1)).sum()),
        "ge1_spof_inside_predicted_4g": int(((rc.n_spof >= 1) & rc.claimed_4g_2026).sum()),
        "radio_chain_inside_predicted_4g": int(rc.claimed_4g_2026.sum()),
        "share_ge1_spof": round(float((rc.n_spof >= 1).mean()), 3),
    }
    # Publicly reported places we are allowed to name (their outages were in the news).
    named = ["Ampilatwatja", "Galiwinku", "Milingimbi", "Wadeye", "Borroloola"]   # the five reported outages (Table 2)
    N["named_places"] = {n: {k: (None if pd.isna(v) else (int(v) if isinstance(v, (np.integer, float, int)) and k != "chain_class" else v))
                             for k, v in c[c.name.str.lower() == n.lower()][["chain_class", "hops", "n_spof"]].iloc[0].to_dict().items()}
                         for n in named if (c.name.str.lower() == n.lower()).any()}
    lwr = L[L.end_site.notna()]
    N["places"]["named_population_2020"] = {n: int(c[c.name.str.lower() == n.lower()].population_2020.iloc[0]) for n in named
                                             if (c.name.str.lower() == n.lower()).any() and not pd.isna(c[c.name.str.lower() == n.lower()].population_2020.iloc[0])}
    N["fibre_what_if"] = {
        "radio_chain_single_fibre_town": int(rc.single_fibre_town.notna().sum()),
        "larger_places_single_fibre_town": int(lwr.single_fibre_town.notna().sum()),
        "larger_places_with_radio_site": int(len(lwr)),
        "note": "Places whose licensed radio path reaches only one fibre town; a break in that town's fibre would take them down too.",
    }

    # --- 2. Relays that are single points of failure --------------------------
    relays = nw.relay_table(c, net)
    power = ro.power_classes(net)
    relays["power_class"] = relays.site_key.map(power)
    tracks = hazards.load_tracks()
    relay_pts = hazards.to_metric_points(relays)
    relays["cyclones_100km_1980_2026"] = hazards.exposure_counts(relay_pts, tracks, P["hazards"]["exposure_radius_km"]).values
    relays["wet_access_risk"] = relays.dist_sealed_km > P["restore"]["wet_sealed_distance_km"]
    N["relays"] = {
        "spof_relays": int(len(relays)),
        "power_classes": relays.power_class.value_counts().to_dict(),
        "share_unknown_autonomy": round(float((relays.power_class.isin(["P0_unknown", "P4_depot_within_150km"])).mean()), 3),
        "published_autonomy": int(relays.power_class.str.match("P[123]").sum()),
        "median_cyclones_100km": float(relays.cyclones_100km_1980_2026.median()),
        "ge5_cyclones_100km": int((relays.cyclones_100km_1980_2026 >= 5).sum()),
        "far_from_sealed_road": int(relays.wet_access_risk.sum()),
        "on_aboriginal_land_trust": int(relays.get("on_alra_land", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
        "graph_sites_matched_to_mnhp": int(power.str.match("P[123]").sum()),
    }
    pw = pd.read_csv(PROCESSED / "power.csv")
    N["mnhp"] = {"items": int(len(pw)), "distinct_locations": int(pw.drop_duplicates(["lat", "lon"]).shape[0]),
                 "depots": int((pw.power_class == "P4_depot").sum()), "classes": pw.power_class.value_counts().to_dict()}

    # --- 3. Hazard replays -----------------------------------------------------
    events = P["hazards"]["replay_events"]
    rows = []
    for eid, label in events.items():
        for cyc_only in (False, True):
            for r_km in P["hazards"]["replay_radius_sweep_km"]:
                R = ro.replay(c, net, tracks, eid, r_km, cyc_only)
                RL = R[R.larger]
                rows.append({"event_id": eid, "event": label, "radius_km": r_km, "cyclone_only": cyc_only,
                             "footprint_relays": int(R.footprint_relays.iloc[0]),
                             "exposed_larger": int(RL.exposed.sum()), "upstream_only_larger": int(RL.upstream_only.sum()),
                             "exposed_all": int(R.exposed.sum()), "upstream_only_all": int(R.upstream_only.sum()),
                             "people_exposed_larger": int(RL[RL.exposed].population_2020.sum())})
                if r_km == P["hazards"]["replay_radius_km"] and not cyc_only:
                    reg = RL[RL.exposed].land_council.map(public_region).value_counts()
                    rows[-1]["by_land_council"] = {k: suppress(int(v), MIN_PLACES) for k, v in reg.items()}
    rep = pd.DataFrame(rows)
    rep.drop(columns=["by_land_council"], errors="ignore").to_csv(PUBLIC / "replay_summary.csv", index=False)
    main = rep[(rep.radius_km == P["hazards"]["replay_radius_km"]) & (~rep.cyclone_only)]
    N["replay"] = {
        "primary": main.drop(columns=["event_id"]).to_dict(orient="records"),
        "primary_total_exposed_larger": int(main.exposed_larger.sum()),
        "primary_total_upstream_larger": int(main.upstream_only_larger.sum()),
        "sweep_total_exposed_larger": {f"r{r}_{'cyclone' if co else 'system'}": int(g.exposed_larger.sum()) for (r, co), g in rep.groupby(["radius_km", "cyclone_only"])},
        "sweep_total_upstream_larger": {f"r{r}_{'cyclone' if co else 'system'}": int(g.upstream_only_larger.sum()) for (r, co), g in rep.groupby(["radius_km", "cyclone_only"])},
    }

    # --- 4. Repair window: January vs July ------------------------------------
    rep_jan, rep_jul = ro.place_repair(c, net, 1), ro.place_repair(c, net, 7)
    rj = rep_jan.merge(c[["place_key", "larger"]], on="place_key")
    rl = rep_jul.merge(c[["place_key", "larger"]], on="place_key")
    rj, rl = rj[rj.larger], rl[rl.larger]
    N["repair"] = {
        "jan_bands": rj.band.value_counts().to_dict(), "jul_bands": rl.band.value_counts().to_dict(),
        "jan_median_days": float(rj.total.median()), "jul_median_days": float(rl.total.median()),
        "jan_access_dominates": int((rj.access > rj.travel + rj.base).sum()),
        "radio_chain_places": int(len(rj)),
        "median_travel_days": float(rl.travel.median()),
        "median_travel_hours": round(float(rl.travel.median()) * P["restore"]["driving_hours_per_day"], 1),
        "jul_fast_and_jan_slow": int(len(set(rj[rj.total > 14].place_key) & set(rl[rl.band == "<1 d"].place_key))),
    }
    slow = rc[rc.place_key.isin(rj[rj.total > 14].place_key)]
    by_relay = sum(any(net.sites.loc[x, "dist_sealed_km"] > P["restore"]["wet_sealed_distance_km"] for x in r.spof_relays) for r in slow.itertuples())
    N["repair"]["jan_slow_set_by_spof_relay"] = int(by_relay)
    N["repair"]["jan_slow_set_by_own_site_only"] = int(len(slow) - by_relay)
    sweep = []
    for w, s in itertools.product(P["restore"]["w_wet_days_sweep"], P["restore"]["wet_sealed_distance_sweep_km"]):
        t = ro.place_repair(c, net, 1, w_wet=w, sealed_threshold=s).merge(c[["place_key", "larger"]], on="place_key")
        t = t[t.larger]
        sweep.append({"w_wet": w, "sealed_km": s, "gt14d": int((t.total > 14).sum()), "access_dominates": int((t.access > t.travel + t.base).sum())})
    N["repair"]["sweep"] = sweep

    # --- 5. What still works, funded work, coverage flags ------------------------
    fb = ro.fallbacks(c).merge(c[["place_key", "larger", "chain_class"]], on="place_key")
    fL = fb[fb.larger]
    N["fallbacks"] = {
        "larger_with_independent_fallback": int(fL.independent_fallback.sum()),
        "larger_with_other_carrier_10km": int((fL.other_carrier_site > 0).sum()),
        "radio_chain_with_other_carrier": int(((fL.chain_class == "radio-chain") & (fL.other_carrier_site > 0)).sum()),
        "radio_chain_with_independent_fallback": int(((fL.chain_class == "radio-chain") & fL.independent_fallback).sum()),
        "radio_chain_with_payphone_3km": int(((fL.chain_class == "radio-chain") & ((fL.get("community_payphone", 0) + fL.get("ric_payphone", 0)) > 0)).sum()),
        "larger": int(len(fL)),
    }
    fd = ro.funded_flags(c).merge(c[["place_key", "larger"]], on="place_key")
    N["funded"] = {k: int(fd[fd.larger][k].sum()) for k in ("mbsp_in_progress", "fn_wifi_2026_leo", "fn_wifi_2026_geo")}
    N["coverage_flags"] = {
        "claimed_4g_all": int(c.claimed_4g_2026.sum()), "all": int(len(c)),
        "claimed_4g_larger": int(L.claimed_4g_2026.sum()),
        "radio_chain_claimed_covered": int(rc.claimed_4g_2026.sum()),
        "register_not_recorded": int((c.mobile_2021 == "Not recorded").sum()),
        "register_N": int((c.mobile_2021 == "N").sum()),
        "register_N_now_claimed": int(((c.mobile_2021 == "N") & c.claimed_4g_2026).sum()),
        "nbn_satellite_only_share": round(float((~c.nbn_fixed_line & ~c.nbn_fixed_wireless).mean()), 3),
    }
    # --- 5b. Cross-check the serving-site assumption against ACCC site data -----
    # The model takes the nearest licensed radio site as the one serving a place.
    # If that site is a Telstra mobile site in the ACCC list, the chain ends where
    # the community's service starts. The second count shows how much of Telstra's
    # NT mobile network the licensed radio graph can see at all.
    ts = pd.read_csv(PROCESSED / "telstra_mobile_sites.csv")
    km = P["checks"]["accc_match_km"]
    ends = net.sites.loc[rc.end_site.values]
    d_end = np.array([haversine_km(a, b, ts.lat.values, ts.lon.values).min() for a, b in zip(ends.lat, ends.lon)])
    spof = rc.n_spof.values >= 1
    d_ts = np.array([haversine_km(a, b, net.sites.lat.values, net.sites.lon.values).min() for a, b in zip(ts.lat, ts.lon)])
    N["accc_check"] = {
        "match_km": km,
        "radio_chain_places": int(len(rc)),
        "radio_chain_end_is_mobile_site": int((d_end <= km).sum()),
        "ge1_spof_places": int(spof.sum()),
        "ge1_spof_end_is_mobile_site": int((d_end[spof] <= km).sum()),
        "unmatched_min_km": round(float(d_end[d_end > km].min()), 1) if (d_end > km).any() else None,
        "telstra_mobile_sites_2026": int(len(ts)),
        "telstra_sites_on_radio_graph": int((d_ts <= km).sum()),
        "share_on_radio_graph": round(float((d_ts <= km).mean()), 3),
    }
    # --- 5c. Stricter test: only links wide enough to carry a 4G site's traffic -----
    # 25 kHz VHF/UHF and 1-2 MHz thin-route channels are licensed point-to-point links,
    # but too narrow for 4G backhaul. Rebuild the chains with wider links only.
    bw = P["checks"]["wide_link_mhz"]
    net_w = nw.load(min_bw_mhz=bw)
    cw = nw.classify(nw.assign_end_sites(pd.read_csv(PROCESSED / "places.csv"), net_w), net_w)
    rw = cw[cw.larger & (cw.chain_class == "radio-chain")]
    head = set(rc[rc.n_spof >= 1].place_key)
    both = rw[(rw.n_spof >= 1) & rw.place_key.isin(head)]
    N["wide_links"] = {
        "min_bw_mhz": bw,
        "links_total": int(net.G.number_of_edges()), "links_wide": int(net_w.G.number_of_edges()),
        "radio_chain_places": int(len(rw)), "with_ge1_spof": int((rw.n_spof >= 1).sum()),
        "people_ge1_spof": int(rw[rw.n_spof >= 1].population_2020.sum()),
        "headline_places_still_flagged": int(len(both)), "headline_places": int(len(head)),
        "people_still_flagged": int(both.population_2020.sum()),
    }

    # --- 5d. Reach of Recommendation 1: chains that end at a co-funded Telstra site ---
    cof = ts[ts.co_funded]
    d_cof = np.array([haversine_km(a, b, cof.lat.values, cof.lon.values).min() if len(cof) else np.inf
                      for a, b in zip(ends.lat, ends.lon)])
    reach = rc.assign(cofunded_end=d_cof <= km)
    flagged = reach[reach.n_spof >= 1]
    relays_reached = set().union(*[set(x) for x in flagged[flagged.cofunded_end].spof_relays]) if flagged.cofunded_end.any() else set()
    all_spof = set().union(*[set(x) for x in c[c.n_spof >= 1].spof_relays])
    ntc = ts[ts.nt_program]
    d_nt = np.array([haversine_km(a, b, ntc.lat.values, ntc.lon.values).min() for a, b in zip(ends.lat, ends.lon)])
    nt_end = flagged.index.isin(rc.index[d_nt <= km]) & flagged.cofunded_end.values
    relays_nt = set().union(*[set(x) for x in flagged[nt_end].spof_relays]) if nt_end.any() else set()
    N["co_investment_reach"] = {
        "telstra_sites_cofunded": int(len(cof)), "telstra_sites_nt_program": int(len(ntc)),
        "flagged_places_nt_program_end": int(nt_end.sum()),
        "spof_relays_on_nt_program_chains": int(len(relays_nt & all_spof)),
        "flagged_places": int(len(flagged)), "flagged_places_cofunded_end": int(flagged.cofunded_end.sum()),
        "people_cofunded_end": int(flagged[flagged.cofunded_end].population_2020.sum()),
        "spof_relays_total": int(len(all_spof)), "spof_relays_on_cofunded_chains": int(len(relays_reached & all_spof)),
    }

    namc = pd.read_csv(PROCESSED / "namc_tiles.csv")
    N["namc"] = {"tiles": int(len(namc)), "feedback": namc.feedback.value_counts().to_dict()}
    led = pd.read_csv(PROCESSED / "outage_ledger.csv")
    hrs = pd.to_numeric(led[led.nt_only].duration.astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    N["outage_ledger"] = {"nbn_rows_including_nt": int(len(led)), "nbn_nt_only_rows": int(led.nt_only.sum()),
                          "nbn_nt_only_hours_min": float(hrs.min()), "nbn_nt_only_hours_max": float(hrs.max())}
    N["network"]["p2p_link_records"] = json.loads((PROCESSED / "prepare_meta.json").read_text())["p2p_rows"]

    # --- 6. Structural sensitivity: 3 anchor radii x 3 end-site radii ------------
    classes = {}
    stats = []
    for a_km, e_km in itertools.product(P["network"]["anchor_radius_sweep_km"], P["network"]["end_site_radius_sweep_km"]):
        _, cc = base_run(a_km, e_km)
        ll = cc[cc.larger]
        classes[(a_km, e_km)] = ll.set_index("place_key").chain_class
        r_ = ll[ll.chain_class == "radio-chain"]
        stats.append({"anchor_km": a_km, "end_km": e_km, "radio_chain": int(len(r_)),
                      "ge1_spof": int((r_.n_spof >= 1).sum()), "ge3_spof": int((r_.n_spof >= 3).sum())})
    M = pd.DataFrame(classes)
    stable = M.nunique(axis=1) == 1
    N["sensitivity"] = {
        "runs": len(stats), "table": stats,
        "larger_places_same_class_all_runs": int(stable.sum()), "larger_places": int(len(M)),
        "robust_share": round(float(stable.mean()), 3),
        "radio_chain_stable_all_runs": int((stable & (M[(10, 10)] == "radio-chain")).sum()),
        "ge1_spof_range": [min(s["ge1_spof"] for s in stats), max(s["ge1_spof"] for s in stats)],
        "ge3_spof_range": [min(s["ge3_spof"] for s in stats), max(s["ge3_spof"] for s in stats)],
        "ge1_spof_share_range": [round(min(s["ge1_spof"] / s["radio_chain"] for s in stats), 3), round(max(s["ge1_spof"] / s["radio_chain"] for s in stats), 3)],
    }

    # --- 7. Region table for public outputs (suppressed) ------------------------
    reg = L.assign(land_council=L.land_council.map(public_region)).groupby(["land_council", "chain_class"]).size().unstack(fill_value=0)
    reg.to_csv(RESTRICTED / "region_classes_unsuppressed.csv")
    reg.map(lambda v: suppress(v, MIN_PLACES)).to_csv(PUBLIC / "region_classes.csv")
    N["regions"] = {lc: {k: suppress(int(v), MIN_PLACES) for k, v in row.items()} for lc, row in reg.iterrows()}

    # --- Write -------------------------------------------------------------------
    c.assign(spof_relays=c.spof_relays.map(lambda x: ";".join(x))).to_csv(RESTRICTED / "place_chains.csv", index=False)
    relays.to_csv(RESTRICTED / "relay_register.csv", index=False)
    fb.to_csv(RESTRICTED / "fallbacks_by_place.csv", index=False)
    pd.concat([rep_jan, rep_jul]).to_csv(RESTRICTED / "repair_by_place.csv", index=False)
    N["_generated_by"] = "src/underlink/pipeline.py"
    # Lineage: the exact inputs behind these numbers, so a stale numbers.json can be spotted.
    import hashlib
    md5 = lambda f: hashlib.md5(f.read_bytes()).hexdigest()   # noqa: E731
    N["_inputs"] = {f.name: md5(f) for f in sorted(PROCESSED.glob("*.csv")) if not f.name.startswith("._")}
    N["_inputs"]["params.yaml"] = md5(PROCESSED.parents[1] / "config" / "params.yaml")
    (PUBLIC / "numbers.json").write_text(json.dumps(N, indent=2, default=lambda o: int(o) if isinstance(o, np.integer) else float(o) if isinstance(o, np.floating) else str(o)))
    return N


if __name__ == "__main__":
    n = run()
    print(json.dumps({k: v for k, v in n.items() if k in ("network", "chains", "relays", "replay", "repair", "sensitivity", "fallbacks", "fibre_what_if", "named_places")}, indent=1, default=str)[:6000])
