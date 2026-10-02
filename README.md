# Underlink

**From Signal to System**

Entry for the CDU IT Code Fair 2026 Data Innovation Challenge (remote connectivity). Team Top Enders (registration DIC017): Harsh Rastogi and Aashish.

- **Web app (public numbers only):** https://underlink-nt.vercel.app
- **Code:** https://github.com/harshrastogii/underlink-nt

A coverage map shows whether a remote community has a mobile signal. It does not show what that signal depends on. Many NT community towers reach the wider network over a chain of licensed radio relays, up to six links long. If one relay in the chain fails and there is no other path, the community loses mobile service even when its own tower is fine. Underlink builds that relay network from the public ACMA licence register, finds each community's chain back to fibre, and marks the relays that have no alternative path (single-path relays). It then asks four more questions of those relays and keeps each answer separate: which past cyclones would have cut them, what backup power is published for them, how long a repair crew might take to reach them in January and in July, and what still works in the community when the mobile network is down.

## Quick start

If you have the submission ZIP, `data/processed/` is included and the commands below work straight away. The public GitHub repository leaves `data/processed/` out, because with the code it can rebuild the restricted relay register (see Privacy and ethics); rebuild it from the raw public downloads with `python run_all.py --prepare`. `data/processed/` is in the ZIP only so judges can reproduce the results; please do not pass it on. On the public repository, pytest runs every check that needs no processed data; the rest run on the submission ZIP.

```bash
pip install -r requirements.txt
python run_all.py                # rebuilds numbers.json and Figures 1 to 5, a few seconds
python scripts/layers_map.py     # redraws Figure I1 (needs internet for the base map)
panel serve app/app.py           # the app, at http://localhost:5006/app
```

`python run_all.py` should end with:

```
Done. 18 of 23 radio-chain places depend on at least one relay with no alternative licensed path; ...
```

Other ways in:

- `notebooks/01_walkthrough.ipynb` walks through the method step by step with the Python commented.
- `outputs/public/underlink_lite.html` is the public view as one offline file. Open it in any browser, no install needed. Rebuild with `python scripts/export_lite.py`.
- `outputs/community_samples/sample_card.pdf` is a one-page "when the phone goes down" card for a made-up community. Rebuild with `PYTHONPATH=src python -m underlink.cards`.
- `pytest -q tests/` runs the checks on the numbers, the method, the privacy rules and the publication rules.
- `web/` is the public web app (plain HTML, CSS and JavaScript, no build step). See "Web app" below.

## What the numbers say

Every number below is read from `outputs/public/numbers.json`, which `run_all.py` writes. The report, deck and app quote the same file.

We looked at the 782 places in the NT Government 2021 remote communities list. The 116 larger ones (towns, major and minor communities, villages) carry the headline counts.

- **The network.** Telstra's licensed point-to-point radio links in the NT form a graph of 358 sites and 313 links in 51 separate pieces. The radio graph has 6 independent loops on its own, and 20 once fibre towns are joined. Most of the network is a set of trees, and in a tree every relay is a single point of failure for everything beyond it.
- **Chains.** Of the 116 larger places, 34 have a fibre-connected site nearby, 23 reach fibre over a radio chain, 14 have radio links but no licensed radio path to fibre, and 45 have no licensed point-to-point site within 10 km.
- **Single-path relays.** 18 of the 23 radio-chain places depend on at least one single-path relay, meaning a relay with no alternative licensed path to fibre. 12 depend on three or more. About 7,100 people live in those 18 places. The median chain is 4 hops, the longest 6.
- **One fibre town.** 39 of the 71 larger places with a radio site reach only one fibre town over licensed radio. A fibre break in that town would take them down too.
- **Power.** Across all 782 places there are 68 single-path relays. None is in the Mobile Network Hardening Program, so their battery hours are not public. 49 have no published backup information at all; for the other 19 the only published fact is a portable generator depot within 150 km.
- **Cyclone replays.** Five past systems (Monica 2006, Lam 2015, Trevor 2019, Megan 2024, Narelle 2026), with relays within 100 km of the track removed, would have cut 22 larger-place paths to fibre. In 4 of those the storm never came within 100 km of the place or its tower; a relay upstream was in the footprint. With a 50 km or 150 km footprint the total is 13 or 25.
- **Repair window.** For the 23 radio-chain places, the median indicative time to restore the slowest element on the chain is 0.9 days in July and 30.8 days in January. In January, 17 of the 23 are over 14 days because a radio site on their chain is more than 10 km from a sealed road.
- **What still works.** 8 of the 23 radio-chain places have a satellite-backed Wi-Fi phone or STAND Sky Muster service within 3 km. 1 has another carrier's mobile site within 10 km.
- **Coverage maps.** 19 of the 23 radio-chain places, and 16 of the 18 with a single-path relay, sit inside Telstra's predicted 4G outdoor footprint.
- **Checked against ACCC site data.** For 16 of the 18 places with a single-path relay (19 of all 23 radio-chain places), the chain ends at a site the ACCC 2026 list shows as a Telstra mobile site (within 1.5 km: 1 km plus the rounding of shipped coordinates). The other chains end at least 12 km from one. Only 85 of Telstra's 274 NT mobile sites (31%) sit on the licensed radio graph; the rest run on fibre, satellite or links the register does not show.
- **Stricter link test.** Counting only links whose licensed channel is wider than 2 MHz (wide enough to carry 4G backhaul), 11 of the 18 places stay flagged (3,663 people). This is a lower bound: the thin links we drop may still be real paths.
- **Where the three layers stand (Appendix I).** 16 of the 18 flagged places also wait over 14 days for a wet-season repair, so a satellite second path at the tower helps most there. 7 of the 18 have a STAND satellite site within 3 km. None of the 23 radio-chain places has a published 1% AEP flood study, and 9 of 358 radio sites (1 single-path relay) sit in a mapped flood area. `scripts/layers_map.py` draws Figure I1 on the Geoscience Australia National Base Map.
- **Co-investment reach.** 6 of the 18 flagged chains end at a Telstra site the ACCC list marks as built with government co-funding (1,527 people). 5 of those sites were funded under NT programs; their chains hold 9 of the 68 single-path relays. The sixth is a Commonwealth Mobile Black Spot site.
- **Sensitivity.** We reran the chain analysis with the two distance assumptions each set to 5, 10 and 15 km. The share of radio-chain places with a single-path relay stays between 78% and 84% across the 9 runs. 18 places are radio-chain places in every run.

## How it works

1. **Build the graph.** Each Telstra point-to-point licence in the ACMA register is an edge between two sites. A site within 10 km of a fibre town (NTG 2019 backhaul list plus the five regional centres) is treated as fibre-connected.
2. **Find each place's site.** The nearest licensed radio site within 10 km stands in for the tower that serves the place.
3. **Find single-path relays.** Join every fibre-connected site to one source node and compute the dominator tree from it (`networkx.immediate_dominators`). A relay that dominates a place's site lies on every path from that site to fibre. Those relays are the chain in `network.chain_of()`.

The chain analysis and four other measures are reported side by side and never merged into one score.

| Measure | Question | Code |
|---|---|---|
| Chain | Which relays have no alternative path? | `network.classify()` |
| Hazard replay | If the relays near a past cyclone track failed, which places lose their path? Direct or upstream only? | `readouts.replay()` |
| Power | What backup power is published for each relay? | `readouts.power_classes()` |
| Repair window | Base time + travel + wet-season access, January vs July | `readouts.repair_days()`, `place_repair()` |
| What still works | Satellite phones, payphones, Wi-Fi hubs and other carriers nearby | `readouts.fallbacks()` |

Every assumption (distances, speeds, days until wet-season access reopens) is in `config/params.yaml`, tagged `source` or `ASSUMPTION`. The assumptions that move results are swept in `pipeline.run()` and the ranges are in `numbers.json`.

The results are also exported as a star schema for a data warehouse: `python -m underlink.schema` writes the tables, `docs/schema.sql` has the DDL for DuckDB or PostgreSQL, and `docs/data_dictionary.md` describes each column.

## Web app

`web/` is a static site: `index.html`, `styles.css`, the scripts `app.js`, `maps.js`, `offgrid.js` and `pipeline.js`, and the data files in `web/data/`. It needs no build step and no internet once loaded. Open `web/index.html` in a browser, or serve it with `python -m http.server 8000 --directory web`.

It shows the public tier only. `scripts/export_web_data.py` (run by `run_all.py`) writes `web/data/public.js` from `outputs/public/` and `config/rules.yaml`, so the app quotes the same numbers as the report. The "break a link" network is made up; no real relay location, site key or per-place result is in `web/`, and `tests/test_public_outputs.py` checks that.

Besides the numbers, the app has:

- **An animated pipeline** (Method): data moving from the public sources to the three outputs.
- **Three layers when the chain breaks** (Off-grid): a seven-step animation. Layer 1 keeps the tower on air with a satellite second path (LEO backhaul, with L-band for heavy rain); layer 2 brings a network to the evacuation centre (NBN STAND satellite trucks and kits, cells on wheels); layer 3 is the community's own radios (Bluetooth apps such as Bitchat and Columba; solar LoRa radios with Meshtastic or Reticulum, legal at 915 to 928 MHz under the ACMA LIPD Class Licence 2025). A table says who owns and pays for each layer. None of the layers reaches 000 from a phone with no signal. Report Appendix H has the sources.
- **A hazard map** (Hazards), with two planning layers: the NT Planning Scheme's published 1% AEP flood studies and the STAND satellite sites at evacuation centres and fire depots (positions only, no names; built by `scripts/hazards_snapshot.py --base`). Hazard layers: fire hotspots (Geoscience Australia DEA Hotspots), road closures, damage, flooding and roadworks (NT Road Report) and current Bureau of Meteorology warnings on a real base map: the Geoscience Australia National Base Map (CC BY 4.0, the default), Esri World Imagery or Esri World Topographic (Esri terms: attribution, non-commercial use). Leaflet 1.9.4 is bundled in `web/vendor/leaflet`, so the map works when the CDN is blocked. Pick the layers, and the legend in the map follows; save it as a PNG or as a PDF through the print dialog. Without internet the base map falls back to the NT outline in `web/data/nt_base.js`. The feeds send no CORS headers, so `scripts/hazards_snapshot.py` writes a snapshot to `web/data/hazards.js`, and a GitHub Action (`.github/workflows/hazards.yml`) reruns it every three hours. Underlink adds no relay, site or community data; road names are left out because some match community names.

Every animation stops under `prefers-reduced-motion`, and the numbered steps under each one say the same thing in words.

To deploy on Vercel: import the GitHub repository, set **Root Directory** to `web`, leave the framework as **Other** with no build command, and deploy. The project name `underlink-nt` gives https://underlink-nt.vercel.app.

## Data and licences

All inputs are public. Sources, URLs, licences and attribution lines are in [DATA_LICENCES.md](DATA_LICENCES.md). [data/manifest.csv](data/manifest.csv) lists every raw file with its retrieval date (29 September 2026), md5 and the processed table it feeds. Regenerate it with `PYTHONPATH=src python -m underlink.manifest`.

Three sources have no stated licence or one we have not confirmed (the First Nations Community Wi-Fi 2026 list, the nbn outage register and the National Audit of Mobile Coverage data). They are marked in DATA_LICENCES.md.

## Privacy and ethics

The full rules are in [docs/ETHICS.md](docs/ETHICS.md). In short:

- **We study relays and paths.** No output describes a person.
- **Two tiers.** Public outputs (`outputs/public/`, `docs/`, the Lite HTML, the card) give counts for two land council groups only (Central; and Northern, Tiwi and Anindilyakwa together), so no small count can be recovered from the published totals. People counts under 10 are suppressed. Relay keys, relay locations and per-place chains stay in `outputs/restricted/`, which is not shipped and is ignored by git.
- **Hashed ids, rounded coordinates.** Radio site ids are replaced by salted hashes and shipped coordinates are rounded to 0.01 degrees (about 1 km).
- **Consent before publication.** `src/underlink/governance.py` encodes who may move an output towards publication. Code can only compute. Only the custodian a community chooses can approve, publish onward or withhold.
- **No community has reviewed any output of this project.** Everything here is built from published data. Any use with communities needs their agreement, ethics approval and land council permits first.

The tests check the privacy rules: `test_public_outputs.py` scans public files for relay keys, coordinate columns and per-place tables, and `test_suppression.py` checks small cells.

## Reproducing from raw data

`docs/REFRESH.md` is the runbook for a monthly refresh: which source changes how often, the order of the steps,
who keeps the salt, and how to re-baseline the pinned tests. `scripts/extract_acma.py` turns the ACMA RRL bulk
download into the NT point-to-point extract.

```bash
python run_all.py --prepare
```

This rebuilds `data/processed/` from the raw downloads in `data_probe/` (about 2 GB). The raw files are not shipped. Their URLs and md5 hashes are in `data/manifest.csv`, and the paths `prepare.py` expects are in the `raw_path` column. Without them, `python run_all.py` works from the shipped `data/processed/` tables.

A fresh `--prepare` run creates a new salt, so relay keys will differ from ours. The counts will not.

## Limitations

- **Licensed radio only.** We see point-to-point links in the ACMA register. Fibre routes, satellite backhaul and unlicensed links are invisible to us. A place with radio links but no licensed radio path to fibre may well have satellite or fibre backhaul we cannot see, and a relay we call single-path may have a fibre bypass.
- **Nearest site is not the serving site.** We assume the nearest licensed radio site within 10 km serves the place. The sensitivity runs vary this distance from 5 to 15 km, and the ACCC check confirms a Telstra mobile site at the end of 16 of the 18 flagged chains.
- **Replays show exposure, not events.** A replay removes every relay within a distance of a track. It does not say those relays failed, and we have no relay-level outage records to check it against.
- **Repair days are assumptions.** Crew bases, speeds and the 30 days until wet-season access reopens are our choices, shown as a breakdown, not a prediction.
- **Power is mostly unknown.** "No published backup" means the battery hours are not public. It does not mean there is no battery.
- **Population is 2020.** From the Bushfires NT list, matched by name and distance. 11 places have no match. 298 of 782 places have no 2020 figure: 11 have no match and 287 match a row with no population.

## Repository structure

```
run_all.py                 regenerate numbers and figures (--prepare to start from raw)
config/params.yaml         every parameter, tagged source or ASSUMPTION
src/underlink/
  prepare.py               raw downloads -> data/processed (hashing, rounding)
  network.py               radio graph, dominators, chain classes
  readouts.py              hazard replay, power, repair window, fallbacks
  hazards.py               cyclone tracks and footprints
  pipeline.py              runs everything, writes numbers.json
  schema.py                star schema export for a warehouse
  manifest.py              data/manifest.csv
  governance.py            publication state machine and suppression helper
  cards.py                 community card PDF
  app_data.py              data for the app
app/app.py                 Panel app (Explorer, Government, Community tabs)
notebooks/                 walkthrough notebook
scripts/                   figures, Lite HTML export, web data, hazard snapshot, ACMA extract
data/processed/            shipped inputs (hashed, rounded)
data/manifest.csv          sources, licences, md5
outputs/public/            numbers.json, public CSVs, figures, Lite HTML
outputs/community_samples/ sample card
outputs/restricted/        not shipped: relay register, per-place chains, warehouse
docs/                      ETHICS.md, schema.sql, data_dictionary.md
web/                       public web app (static; data/public.js from export_web_data.py)
tests/                     pytest checks
```

## Tested on

macOS with Python 3.12. Package versions are pinned in `requirements.txt`.

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data keep their own licences (see [DATA_LICENCES.md](DATA_LICENCES.md)). Any community language text, recordings, symbols or local knowledge added to a card belong to that community. They are not covered by the MIT licence and are not reused without the community's consent.
