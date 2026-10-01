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
