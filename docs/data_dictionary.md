# Underlink data dictionary

This describes the warehouse tables written by `python -m underlink.schema` to
`outputs/restricted/warehouse/`. The DDL is in `docs/schema.sql` and loads in
DuckDB or PostgreSQL.

The warehouse is **restricted**. `dim_site` and `fact_chain_member` hold relay
keys. The keys are salted hashes (`R` followed by 8 hex characters), so they
cannot be matched back to the ACMA register without the salt, which also stays
in the restricted folder. No table holds a community name or a coordinate.

One snapshot is loaded: 2026-09-29, variant V1 (fibre-connected sites are
treated as sound). Dimensions carry `valid_from` and `valid_to` so a later
snapshot can be added as new rows.

## Shape

```
              dim_event
                  |
dim_place --- fact_replay_result
    |  \
    |   +---- fact_place_snapshot
    |   +---- fact_fallback
    |   +---- fact_chain_member --- dim_site

fact_outage_event (links to dim_place once a carrier or community names the place)
```

| Table | Grain | Rows (2026-09-29) |
|---|---|---|
| dim_place | one place in the NTG 2021 remote communities list | 782 |
| dim_site | one Telstra licensed point-to-point radio site in the NT | 358 |
| dim_event | one replayed cyclone or tropical low | 5 |
| fact_place_snapshot | one place, per snapshot and variant | 782 |
| fact_chain_member | one site on one shortest radio path from a radio-chain place to fibre | 468 |
| fact_replay_result | one place under one replay (event x radius x track variant) | 23,460 |
| fact_fallback | one place and one fallback channel type | 5,474 |
| fact_outage_event | one published nbn outage that includes the NT | 5 |

## dim_place

Primary key: `place_key`.

| Column | Type | Meaning |
|---|---|---|
| place_key | text | `P0000` to `P0781`, in the row order of the NTG 2021 list |
| ntg_type | text | NTG `COMMUNITY_TYPE`, for example Town, Major, Minor, Village, Family Outstation |
| larger | boolean | True when `ntg_type` is Town, Major, Minor or Village. 116 places. Most headline counts use these. |
| land_council | text | Land council region the place falls in (NTLIS boundaries). This is the unit for public counts. |
| population_2020 | integer | Bushfires NT 2020 population, matched by name and distance. Null for 298 places: 11 have no match in the Bushfires NT list and 287 match a row with no population. People counts in numbers.json add only known values, so they are lower bounds. |
| claimed_4g_2026 | boolean | Place is inside Telstra's predicted 4G outdoor footprint in the ACCC 2026 release. A prediction, not a measurement. |
| mobile_2021 | text | NTG 2021 register field: `Y`, `N` or `Not recorded` |
| valid_from | date | First day this row applies |
| valid_to | date | Last day this row applies. Null means current. |

## dim_site

Primary key: `site_key`.

| Column | Type | Meaning |
|---|---|---|
| site_key | text | Salted hash of the ACMA site id |
| dist_sealed_km | double | Straight-line km to the nearest sealed road (Geoscape National Roads) |
| power_class | text | `P0_unknown`: no published backup power. `P1`-`P3`: a Mobile Network Hardening Program item within 3 km. `P4_depot_within_150km`: within 150 km of a Telstra portable generator depot. P0 means the battery hours are not published. It does not mean there is no battery. |
| is_fibre_connected | boolean | Within 10 km of a fibre town, so treated as a root of the graph |
| valid_from, valid_to | date | As in dim_place |

## dim_event

Primary key: `event_key`. `bom_disturbance_id` is unique.

| Column | Type | Meaning |
|---|---|---|
| event_key | text | `E01` to `E05` |
| bom_disturbance_id | text | `DISTURBANCE_ID` in the BoM best track file |
| label | text | Name and season, for example `Lam 2015` |

## fact_place_snapshot

Primary key: `(place_key, variant, snapshot_date)`. Foreign key: `place_key` to dim_place.

| Column | Type | Meaning |
|---|---|---|
| place_key | text | The place |
| chain_class | text | `at-anchor`: the place's site is fibre-connected. `radio-chain`: reaches fibre over licensed radio relays. `radio-island`: has licensed radio links but no radio path to fibre (probably satellite or backhaul we cannot see). `no-radio-site`: no licensed point-to-point site within 10 km. |
| hops | integer | Radio links from the place's site to fibre. 0 for at-anchor, null for the two classes with no path. |
| n_spof | integer | Relays with no alternative licensed path (single points of failure) |
| variant | text | `V1` |
| snapshot_date | date | `2026-09-29` |

## fact_chain_member

Primary key: `(place_key, position, variant, snapshot_date)`. Foreign keys: `place_key` to dim_place, `site_key` to dim_site. Only radio-chain places have rows.

| Column | Type | Meaning |
|---|---|---|
| place_key | text | The place |
| site_key | text | A site on one shortest radio path from the place's site to fibre |
| position | integer | 0 is the place's own site; the number rises towards fibre |
| role | text | `end_site` (position 0), `relay`, or `fibre_site` (the last site, fibre-connected) |
| is_spof | boolean | True when every licensed path to fibre passes through this relay. These are the dominators of the site in graph terms. Every dominator lies on every path, so all of them appear on this one. The end site and the fibre site are marked false. |
| variant, snapshot_date | | As above |

When a place has more than one shortest path, one is stored. The relays with
`is_spof = false` on that path have at least one alternative.

## fact_replay_result

Primary key: `(event_key, radius_km, track_variant, place_key)`. Foreign keys: `event_key` to dim_event, `place_key` to dim_place.

A replay removes every non-fibre radio site within `radius_km` of the track and
re-traces each place. It shows exposure. It does not say what happened during the event.

| Column | Type | Meaning |
|---|---|---|
| event_key | text | The event |
| radius_km | integer | Footprint half-width: 50, 100 or 150 km |
| track_variant | text | `system`: every fix, including the tropical low and ex-cyclone stages. `cyclone_only`: segments at gale strength (17.5 m/s) or more. |
| place_key | text | The place |
| status | text | `not_affected`: kept its path, or never had one. `direct`: lost its path and the place or its own site was in the footprint. `upstream_only`: lost its path although the storm did not reach the place or its site; a relay it depends on was in the footprint. |

## fact_fallback

Primary key: `(place_key, channel_type)`. Foreign key: `place_key` to dim_place.

| Column | Type | Meaning |
|---|---|---|
| place_key | text | The place |
| channel_type | text | `wifi_phone`, `community_payphone`, `ric_payphone`, `wifi_hub`, `community_wifi_nbn`, `stand_sky_muster`, `other_carrier_site` |
| count_within_km | integer | How many of this channel lie within `radius_km` of the place |
| radius_km | integer | 3 km for channels people walk to; 10 km for another carrier's mobile site |
| independence | text | Whether the channel uses a path separate from the Telstra mobile network. Wi-Fi phones and STAND Sky Muster run over satellite. For payphones we do not know, so the value says to ask locally. |

## fact_outage_event

Primary key: `outage_key`. Foreign key: `place_key` to dim_place, empty until a carrier
(Recommendation 3) or a community custodian (Recommendation 6) names the place. Public
registers name towns, not sites, so published rows stay unlinked.

| Column | Type | Meaning |
|---|---|---|
| outage_key | text | `O001` onwards |
| source | text | `nbn register` |
| title | text | Title as published |
| start_date, end_date | date | Converted from the register's dd/mm/yyyy |
| duration_hours | double | Duration as published. The register does not label the unit; the values read as hours. |
| states | text | States and territories affected, as published |
| cause | text | High-level cause, as published |
| nt_only | boolean | True when the NT is the only territory listed |
| place_key | text | Place the outage hit, if known; empty for register rows |
| recorded_by | text | `nbn register`, a carrier, or a community custodian |

The view `v_outage_hours_per_place` sums outage hours per place per wet season
(November to April). It is the Recommendation 3 KPI.

## Example query

The headline count (18 of 23 larger radio-chain places depend on at least one
relay with no alternative licensed path):

```sql
SELECT count(*) FILTER (WHERE s.n_spof >= 1) AS with_spof,
       count(*)                              AS radio_chain
FROM fact_place_snapshot s
JOIN dim_place p USING (place_key)
WHERE p.larger AND s.chain_class = 'radio-chain';
```

`tests/test_integrity.py` builds the tables, loads them through
`docs/schema.sql` and checks this query and the replay totals against
`outputs/public/numbers.json`.

## Other files

- `data/processed/*.csv`: the shippable inputs. Coordinates are rounded to 0.01 degrees (about 1 km) and site ids are hashed. See `src/underlink/prepare.py`.
- `data/manifest.csv`: source, publisher, URL, licence, retrieval date, raw path, md5 and processed row count for every raw file.
- `outputs/public/numbers.json`: every number quoted in the report, deck and app.
