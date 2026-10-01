# Refreshing Underlink (runbook for DCDD)

Every number comes from `outputs/public/numbers.json`, which `python run_all.py` rebuilds.
`numbers.json` records the md5 of each processed table and of `config/params.yaml` under
`_inputs`, and `test_numbers_json_matches_its_inputs` fails if any input changed without a rerun.

## How often each source changes

| Source | Changes | Refresh |
|---|---|---|
| ACMA Register of Radiocommunications Licences | daily | monthly, and before each wet season |
| ACCC Mobile Infrastructure Report data | yearly | when a new release appears |
| NTG remote communities registers (2019, 2021) | rarely | when NTG publishes a new list |
| BoM tropical cyclone best track | after each season | each May |
| Mobile Network Hardening Program, STAND, MBSP layers | a few times a year | quarterly |
| Carrier outage registers (ACMA rule from 30 June 2026) | continuously | monthly, into `fact_outage_event` |

## Steps

1. Download the raw files listed in `data/manifest.csv` into `data_probe/`, at the paths in its `raw_path` column.
   For the ACMA register, unzip the RRL bulk download (spectra_rrl.zip) into `data_probe/listed-datasets/acma/`
   and run `python scripts/extract_acma.py`. It pairs each transmitter with its receiver (RELATED_EFL_ID) and
   writes `nt_p2p_links.csv`; `--check` compares a rebuild with the existing file (it matches 1,961 of 1,961 rows).
2. `python run_all.py --prepare` rebuilds `data/processed/` and every output.
3. `PYTHONPATH=src python -m underlink.manifest` updates the md5s and row counts.
4. `pytest -q tests/`. Tests that pin values from the 29 September 2026 snapshot (for example 358 sites,
   18 of 23) will fail on new data by design: read the diff in `numbers.json`, then update the pinned
   values in `tests/test_integrity.py` in the same change.
5. `python -m underlink.schema` writes the star schema; load it with `docs/schema.sql`
   (DuckDB or PostgreSQL).

## Keys and the salt

- `site_key` is a salted hash of the ACMA site id. The salt (`outputs/restricted/site_salt.txt`) stays with
  the data custodian at DCDD. Keep it: a new salt gives new keys, and warehouse history would no longer join.
- `place_key` is the row order of the NTG 2021 list. If NTG publishes a new list, map old keys to new ones
  by name and location before loading, so place history keeps its key.

## Known gaps

- Public outage registers name towns, not sites, so `fact_outage_event.place_key` stays empty until a
  carrier (Recommendation 3) or a community custodian (Recommendation 6) names the place.
