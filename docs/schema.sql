-- Underlink warehouse schema (star schema), DuckDB and PostgreSQL compatible.
--
-- Build the CSVs:   python -m underlink.schema   (writes outputs/restricted/warehouse/)
-- Load in DuckDB:   run this file, then
--                   COPY dim_place FROM 'outputs/restricted/warehouse/dim_place.csv' (HEADER);
--                   and the same for each table, dimensions first.
-- Load in Postgres: run this file, then \copy each table FROM its CSV WITH (FORMAT csv, HEADER).
--
-- Tier: RESTRICTED. dim_site and fact_chain_member hold salted, hashed relay
-- keys. No table holds a community name or a coordinate.
--
-- Snapshot handling: dimensions carry valid_from / valid_to. This release has
-- one snapshot (2026-09-29), so place_key and site_key are unique on their own.
-- A second snapshot would add a surrogate key and close valid_to on old rows.

-- ---------------------------------------------------------------- dimensions

CREATE TABLE dim_place (
    place_key        VARCHAR PRIMARY KEY,   -- P0000..P0781, row order of the NTG 2021 register
    ntg_type         VARCHAR NOT NULL,      -- NTG COMMUNITY_TYPE (Town, Major, Minor, Village, Family Outstation, ...)
    larger           BOOLEAN NOT NULL,      -- ntg_type in Town/Major/Minor/Village (116 places)
    land_council     VARCHAR NOT NULL,      -- public aggregation unit
    population_2020  INTEGER,               -- Bushfires NT 2020; NULL when no match
    claimed_4g_2026  BOOLEAN NOT NULL,      -- inside Telstra's predicted 4G outdoor footprint (ACCC 2026)
    mobile_2021      VARCHAR NOT NULL CHECK (mobile_2021 IN ('Y', 'N', 'Not recorded')),
    valid_from       DATE NOT NULL,
    valid_to         DATE                   -- NULL = current
);
COMMENT ON TABLE dim_place IS 'One row per place in the NTG 2021 remote communities list. No names or coordinates.';

CREATE TABLE dim_site (
    site_key            VARCHAR PRIMARY KEY,  -- R + 8 hex chars, salted hash of the ACMA site id
    dist_sealed_km      DOUBLE PRECISION NOT NULL,      -- straight-line km to nearest sealed road (Geoscape)
    flood_1pc_km        DOUBLE PRECISION NOT NULL,      -- km to the nearest published 1% AEP flood study area (NT Planning Scheme, NTLIS)
    power_class         VARCHAR NOT NULL,     -- P0_unknown, P1..P3 (MNHP item within 3 km), P4_depot_within_150km
    is_fibre_connected  BOOLEAN NOT NULL,     -- within 10 km of a fibre town (a graph root)
    valid_from          DATE NOT NULL,
    valid_to            DATE
);
COMMENT ON TABLE dim_site IS 'One row per Telstra licensed point-to-point radio site in the NT. RESTRICTED.';

CREATE TABLE dim_event (
    event_key           VARCHAR PRIMARY KEY,  -- E01..E05
    bom_disturbance_id  VARCHAR NOT NULL UNIQUE,  -- BoM best track DISTURBANCE_ID
    label               VARCHAR NOT NULL          -- e.g. Lam 2015
);
COMMENT ON TABLE dim_event IS 'Cyclones and tropical lows replayed against the network.';

-- --------------------------------------------------------------------- facts

CREATE TABLE fact_place_snapshot (
    place_key      VARCHAR NOT NULL REFERENCES dim_place (place_key),
    chain_class    VARCHAR NOT NULL CHECK (chain_class IN ('at-anchor', 'radio-chain', 'radio-island', 'no-radio-site')),
    hops           INTEGER,                 -- radio links from the place's site to fibre; NULL unless at-anchor or radio-chain
    n_spof         INTEGER NOT NULL,        -- relays with no alternative licensed path
    variant        VARCHAR NOT NULL,        -- V1: fibre-connected sites treated as sound
    snapshot_date  DATE NOT NULL,
    PRIMARY KEY (place_key, variant, snapshot_date)
);
COMMENT ON TABLE fact_place_snapshot IS 'Grain: one place per snapshot and variant. Chain class and single points of failure.';

CREATE TABLE fact_chain_member (
    place_key      VARCHAR NOT NULL REFERENCES dim_place (place_key),
    site_key       VARCHAR NOT NULL REFERENCES dim_site (site_key),
    position       INTEGER NOT NULL,        -- 0 = the place's own site, counting up towards fibre
    role           VARCHAR NOT NULL CHECK (role IN ('end_site', 'relay', 'fibre_site')),
    is_spof        BOOLEAN NOT NULL,        -- relay with no alternative path (a dominator)
    variant        VARCHAR NOT NULL,
    snapshot_date  DATE NOT NULL,
    PRIMARY KEY (place_key, position, variant, snapshot_date)
);
COMMENT ON TABLE fact_chain_member IS 'Grain: one site on one shortest radio path from a radio-chain place to fibre. RESTRICTED.';

CREATE TABLE fact_replay_result (
    event_key      VARCHAR NOT NULL REFERENCES dim_event (event_key),
    radius_km      INTEGER NOT NULL,        -- footprint half-width: 50, 100 or 150
    track_variant  VARCHAR NOT NULL CHECK (track_variant IN ('system', 'cyclone_only')),
    place_key      VARCHAR NOT NULL REFERENCES dim_place (place_key),
    status         VARCHAR NOT NULL CHECK (status IN ('not_affected', 'direct', 'upstream_only')),
    PRIMARY KEY (event_key, radius_km, track_variant, place_key)
);
COMMENT ON TABLE fact_replay_result IS 'Grain: one place under one replay. Shows exposure, not what happened.';

CREATE TABLE fact_fallback (
    place_key        VARCHAR NOT NULL REFERENCES dim_place (place_key),
    channel_type     VARCHAR NOT NULL,      -- wifi_phone, community_payphone, ric_payphone, wifi_hub, community_wifi_nbn, stand_sky_muster, other_carrier_site
    count_within_km  INTEGER NOT NULL,      -- how many of this channel lie within radius_km of the place
    radius_km        INTEGER NOT NULL,      -- 3 for walkable fallbacks, 10 for other carriers
    independence     VARCHAR NOT NULL,      -- whether it uses a path separate from the mobile network
    PRIMARY KEY (place_key, channel_type)
);
COMMENT ON TABLE fact_fallback IS 'Grain: one place and one fallback channel type.';

CREATE TABLE fact_outage_event (
    outage_key      VARCHAR PRIMARY KEY,    -- O001..
    source          VARCHAR NOT NULL,       -- nbn register
    title           VARCHAR NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE,
    duration_hours  DOUBLE PRECISION,                 -- as published in the register
    states          VARCHAR NOT NULL,       -- states and territories affected, as published
    cause           VARCHAR,
    nt_only         BOOLEAN NOT NULL,
    place_key       VARCHAR REFERENCES dim_place (place_key),  -- empty until a carrier or community names the place
    recorded_by     VARCHAR NOT NULL        -- 'nbn register', a carrier, or a community custodian (Rec 6)
);
COMMENT ON TABLE fact_outage_event IS 'Grain: one outage. Public registers name towns, not sites, so place_key stays empty until a carrier (Rec 3) or a community (Rec 6) names the place.';

-- Rec 3 KPI: outage hours per radio-chain place per wet season (November to April).
-- Rows without a place_key are not counted; the share of hours with a place is the data-gap measure.
CREATE VIEW v_outage_hours_per_place AS
SELECT p.place_key,
       CASE WHEN EXTRACT(MONTH FROM o.start_date) >= 11 THEN EXTRACT(YEAR FROM o.start_date)
            ELSE EXTRACT(YEAR FROM o.start_date) - 1 END AS wet_season_start_year,
       SUM(o.duration_hours) AS outage_hours
FROM fact_outage_event o
JOIN dim_place p ON p.place_key = o.place_key
WHERE EXTRACT(MONTH FROM o.start_date) IN (11, 12, 1, 2, 3, 4)
GROUP BY 1, 2;
