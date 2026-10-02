"""The headline counts: the graph, the chains, and the warehouse that holds them."""
import json

import duckdb
import pytest

from underlink import network as nw, pipeline, schema
from underlink.config import PUBLIC, ROOT


@pytest.fixture(scope="module")
def numbers():
    return json.loads((PUBLIC / "numbers.json").read_text())


def test_graph_integrity():
    # V nodes, E edges, C components; cycle rank = E - V + C independent loops
    got = nw.integrity(nw.load())
    assert {k: got[k] for k in ("V", "E", "C", "cycle_rank_radio", "cycle_rank_with_fibre")} == {
        "V": 358, "E": 313, "C": 51, "cycle_rank_radio": 6, "cycle_rank_with_fibre": 20}


def test_numbers_json_headline(numbers):
    assert numbers["chains"]["radio_chain_places"] == 23
    assert numbers["chains"]["with_ge1_spof"] == 18


def test_accc_crosscheck(numbers):
    # Most chains end at a site the ACCC lists as a Telstra mobile site, so the
    # nearest-site assumption holds for most of the headline places.
    a = numbers["accc_check"]
    assert (a["ge1_spof_end_is_mobile_site"], a["ge1_spof_places"]) == (16, 18)
    assert (a["radio_chain_end_is_mobile_site"], a["radio_chain_places"]) == (19, 23)
    assert a["unmatched_min_km"] > 10    # the misses are far off, not near the cut-off


def test_stricter_link_test_and_co_investment_reach(numbers):
    # Only links wider than 2 MHz can carry 4G backhaul: 11 of the 18 flagged places stay flagged.
    w = numbers["wide_links"]
    assert (w["links_wide"], w["links_total"]) == (102, 313)
    assert (w["headline_places_still_flagged"], w["headline_places"]) == (11, 18)
    # A co-investment condition (Rec 1) reaches the chains that end at a co-funded site: 6 of 18.
    r = numbers["co_investment_reach"]
    assert (r["flagged_places_cofunded_end"], r["flagged_places"]) == (6, 18)
    assert (r["spof_relays_on_cofunded_chains"], r["spof_relays_total"]) == (12, 68)
    # Only NT programs carry an NT condition: 5 of those 6 chains, 9 relays (the sixth is a Commonwealth MBSP site).
    assert (r["flagged_places_nt_program_end"], r["spof_relays_on_nt_program_chains"], r["telstra_sites_nt_program"]) == (5, 9, 25)


def test_recompute_matches_numbers_json(numbers):
    # Recompute from data/processed without rewriting any output file.
    _, c = pipeline.base_run()
    rc = c[c.larger & (c.chain_class == "radio-chain")]
    assert len(rc) == numbers["chains"]["radio_chain_places"]
    assert int((rc.n_spof >= 1).sum()) == numbers["chains"]["with_ge1_spof"]
    assert int((rc.n_spof >= 3).sum()) == numbers["chains"]["with_ge3_spof"]


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    """Build the star schema, write it to a temp folder and load it with docs/schema.sql."""
    d = tmp_path_factory.mktemp("warehouse")
    con = duckdb.connect()
    con.execute((ROOT / "docs" / "schema.sql").read_text())
    for name, df in schema.build().items():
        df.to_csv(d / f"{name}.csv", index=False)
    for name in schema.TABLES:   # dimensions first so foreign keys resolve
        con.execute(f"COPY {name} FROM '{d / (name + '.csv')}' (HEADER)")
    return con


def test_warehouse_loads(warehouse):
    names = {r[0] for r in warehouse.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert set(schema.TABLES) <= names
    assert warehouse.execute("SELECT count(*) FROM dim_place").fetchone()[0] == 782
    assert warehouse.execute("SELECT count(*) FROM dim_site").fetchone()[0] == 358


def test_warehouse_reproduces_headline(warehouse, numbers):
    ge1, total = warehouse.execute("""
        SELECT count(*) FILTER (WHERE s.n_spof >= 1), count(*)
        FROM fact_place_snapshot s JOIN dim_place p USING (place_key)
        WHERE p.larger AND s.chain_class = 'radio-chain'""").fetchone()
    assert (ge1, total) == (numbers["chains"]["with_ge1_spof"], numbers["chains"]["radio_chain_places"])
    spof = warehouse.execute("SELECT count(DISTINCT site_key) FROM fact_chain_member WHERE is_spof").fetchone()[0]
    assert spof == numbers["relays"]["spof_relays"]


def test_warehouse_replay_matches(warehouse, numbers):
    exposed, upstream = warehouse.execute("""
        SELECT count(*) FILTER (WHERE status <> 'not_affected'), count(*) FILTER (WHERE status = 'upstream_only')
        FROM fact_replay_result r JOIN dim_place p USING (place_key)
        WHERE p.larger AND radius_km = 100 AND track_variant = 'system'""").fetchone()
    assert exposed == numbers["replay"]["primary_total_exposed_larger"]
    assert upstream == numbers["replay"]["primary_total_upstream_larger"]


def test_warehouse_has_no_names_or_coordinates(warehouse):
    cols = {r[0] for r in warehouse.execute(
        "SELECT column_name FROM duckdb_columns() WHERE NOT internal AND schema_name = 'main'").fetchall()}
    assert "site_key" in cols   # sanity: the query sees our tables
    assert not cols & {"name", "lat", "lon", "lat_full", "lon_full", "site_id"}


def test_numbers_json_matches_its_inputs(numbers):
    # numbers.json records the md5 of every processed table and params.yaml it was built from.
    import hashlib
    from underlink.config import PROCESSED
    for name, digest in numbers["_inputs"].items():
        f = (PROCESSED.parents[1] / "config" / name) if name == "params.yaml" else PROCESSED / name
        assert hashlib.md5(f.read_bytes()).hexdigest() == digest, f"{name} changed since numbers.json was built: rerun run_all.py"


def test_where_the_three_layers_stand(numbers):
    # Appendix I: 16 of the 18 flagged places also wait over 14 days in the wet (layer 1 matters most there);
    # 7 have a STAND satellite site within 3 km (layer 2); none of the 23 radio-chain places has a published
    # 1% AEP flood study, and 9 radio sites (1 single-path relay) sit in a mapped flood area.
    L = numbers["layers"]
    assert (L["flagged_and_wet_slow"], L["flagged_places"]) == (16, 18)
    assert (L["flagged_with_stand_3km"], L["radio_chain_with_stand_3km"], L["stand_sites_nt"]) == (7, 8, 88)
    assert (L["radio_chain_with_flood_study"], L["radio_sites_in_mapped_flood"], L["spof_relays_in_mapped_flood"]) == (0, 9, 1)


def test_mnhp_match_counts_telstra_items_only(numbers):
    # The graph is Telstra-only, so the two Optus generators at Katherine must not count as power at a Telstra site.
    assert numbers["relays"]["graph_sites_matched_to_mnhp"] == 9
    assert numbers["relays"]["published_autonomy"] == 0
    assert numbers["relays"]["power_classes"]["P4_depot_within_150km"] == 19


def test_link_cleaning_choices_bracket_the_headline(numbers):
    # Dropping the 25 kHz VHF/UHF links: 19 of the same 23, and every one of the 18 headline places stays flagged.
    n = numbers["narrowband_dropped"]
    assert (n["links_kept"], n["radio_chain_places"], n["with_ge1_spof"], n["headline_places_still_flagged"]) == (239, 23, 19, 18)
    # The stricter 4G test keeps 11 at every cut from just under 2 MHz to 28 MHz.
    sweep = {round(s["min_bw_mhz"], 2): (s["links"], s["headline_places_still_flagged"]) for s in numbers["wide_links"]["sweep"]}
    assert sweep == {1.0: (239, 18), 1.99: (203, 11), 2.0: (102, 11), 6.9: (93, 11), 13.9: (91, 11), 27.9: (81, 11)}
    w = numbers["wide_links"]
    assert w["headline_places_still_flagged"] + w["headline_places_lost_path"] == w["headline_places"]
    assert w["named_places"]["Ampilatwatja"] == {"chain_class": "radio-chain", "n_spof": 5}
    assert w["named_places"]["Galiwinku"] == {"chain_class": "radio-island", "n_spof": 0}


def test_printed_counts_are_in_numbers_json(numbers):
    assert numbers["fibre_what_if"]["flagged_single_fibre_town"] == 16
    assert numbers["chains"]["ge1_spof_without_population"] == 2
    assert numbers["accc_check"]["remote_50km"] == {"telstra_sites": 82, "on_radio_graph": 34}


def test_outage_hours_come_from_timestamps():
    import pandas as pd
    from underlink.config import PROCESSED
    o = pd.read_csv(PROCESSED / "outage_ledger.csv")
    assert o.reference.is_unique
    # the register prints 22.36 (22 h 36 min) and 28.4 (28 h 04 min): hours come from start and end times
    raw = pd.read_csv(PROCESSED.parents[1] / "data_probe/nt-connectivity-landscape/nbn_outage_register.csv") \
        if (PROCESSED.parents[1] / "data_probe").exists() else None
    if raw is not None:
        from underlink.prepare import build_outage_ledger
        led = build_outage_ledger().set_index("reference")
        assert led.loc["ACM000000000071", "duration_hours"] == 22.6
        assert led.loc["ACM000000000068", "duration_hours"] == 28.07


def test_fact_tables_key_on_snapshot_date(warehouse):
    # a second monthly load adds rows instead of failing: every fact table but the outage table keys on snapshot_date
    rows = warehouse.execute("SELECT table_name, constraint_column_names FROM duckdb_constraints() "
                             "WHERE constraint_type = 'PRIMARY KEY' AND table_name LIKE 'fact_%'").fetchall()
    keys = {t: list(c) for t, c in rows}
    for t, cols in keys.items():
        if t != "fact_outage_event":
            assert "snapshot_date" in cols, t


def test_wet_season_delay_moves_the_wait(numbers):
    # The delay control changes how long places wait, not which places wait (that comes from road distance).
    rep = numbers["repair"]
    main = next(s for s in rep["sweep"] if s["w_wet"] == 30 and s["sealed_km"] == 10)
    assert main["jan_median_days"] == round(rep["jan_median_days"], 1)
    for km in {s["sealed_km"] for s in rep["sweep"]}:
        med = [s["jan_median_days"] for s in sorted((s for s in rep["sweep"] if s["sealed_km"] == km), key=lambda s: s["w_wet"])]
        assert med == sorted(med) and len(set(med)) == len(med)
