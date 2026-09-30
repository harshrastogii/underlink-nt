"""Write data/manifest.csv: where every input came from and under what licence.

    python -m underlink.manifest

One row per raw file that prepare.py reads. A source with several files (for
example the NTLIS layers) gets one row per file. The md5 is filled in only when
the raw file is present under data_probe/; the raw downloads are not shipped,
so on a judge's machine that column stays as it was last written.
"""
from __future__ import annotations

import csv
import hashlib

import pandas as pd

from .config import PROCESSED, RAW, ROOT

RETRIEVED = "2026-09-29"
OUT = ROOT / "data" / "manifest.csv"
FIELDS = ["source", "publisher", "url", "licence", "retrieved", "raw_path", "raw_md5",
          "processed_table", "processed_rows"]

_DITRDCSA = "Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts"
_FNMT = "https://spatial.infrastructure.gov.au/portal/apps/experiencebuilder/experience/?id=81c5ae65fbf74ce3a89cf25b1f323d50"

# (source, publisher, url, licence, raw path under data_probe/, processed tables it feeds)
SOURCES = [
    ("ACMA Register of Radiocommunications Licences (point-to-point)", "Australian Communications and Media Authority",
     "https://www.acma.gov.au/radiocomms-licence-data",
     "ACMA RRL licence: use and derivatives allowed with attribution",
     "listed-datasets/acma/nt_p2p_links.csv", ["sites", "links"]),
    ("NTG remote communities with mobile coverage 2021", "Northern Territory Government",
     "https://data.nt.gov.au/dataset/remote-communities-with-mobile-coverage", "CC BY",
     "listed-datasets/accc/nt_communities_telstra4g_outdoor_2026.csv", ["places"]),
    ("NTG list of remote communities with mobile coverage (backhaul) 2019", "Northern Territory Government",
     "https://data.nt.gov.au/dataset/list-of-remote-communities-with-mobile-coverage", "CC BY",
     "listed-datasets/ntg/remote-communities-mobile-coverage-backhaul-2019.xlsx", ["anchors", "ntg_backhaul_2019"]),
    ("ACCC Mobile Infrastructure Report data release", "Australian Competition and Consumer Commission",
     "https://data.gov.au/data/dataset/accc-mobile-infrastructure-report-data-release", "CC BY 2.5 AU",
     "listed-datasets/accc/accc_mobile_sites_NT_bbox_2018_2026.csv", ["other_carriers"]),
    ("BoM tropical cyclone best track", "Bureau of Meteorology",
     "https://www.bom.gov.au/clim_data/IDCKMSTM0S.csv", "BoM copyright, reuse with attribution",
     "listed-datasets/cyclone/IDCKMSTM0S.csv", ["tracks"]),
    ("First Nations Connectivity Mapping Tool public layers (AGIL locations)", _DITRDCSA,
     _FNMT, "CC BY 4.0 (public layers)", "listed-datasets/fnmap/nt_agil.geojson", ["funded"]),
] + [
    ("First Nations Connectivity Mapping Tool public layers (payphones, Wi-Fi phones, Wi-Fi hubs, NBN community Wi-Fi)",
     _DITRDCSA + "; NIAA", _FNMT, "CC BY 4.0 (public layers)", f"au-telecom-infra/payphones/{f}", ["fallbacks"])
    for f in ("wifi_telephones_nt.csv", "community_payphones_nt.csv", "payphones_ric_nt.csv",
              "wifi_hubs_nt.csv", "community_wifi_nbn_nt.csv")
] + [
    ("nbn footprint for NT communities", "NBN Co via data.gov.au",
     "https://data.gov.au/data/dataset/national-broadband-network", "CC BY 4.0",
     "listed-datasets/nbn/nt_communities_nbn_footprint.csv", ["places"]),
    ("Mobile Network Hardening Program sites", _DITRDCSA,
     "https://spatial.infrastructure.gov.au/server/rest/services", "CC BY 4.0",
     "au-telecom-infra/mnhp/mnhp_nt_all_layers.csv", ["power"]),
    ("STAND Sky Muster satellite deployments", _DITRDCSA,
     "https://spatial.infrastructure.gov.au/server/rest/services", "CC BY 4.0",
     "au-telecom-infra/stand/stand_skymuster_nt.csv", ["fallbacks"]),
    ("Mobile Black Spot Program base stations", _DITRDCSA,
     "https://spatial.infrastructure.gov.au/server/rest/services", "CC BY 4.0",
     "au-telecom-infra/mbsp/mbsp_nt_kml_points.csv", ["funded"]),
    ("First Nations Community Wi-Fi Program 2026 funded list", _DITRDCSA,
     "https://www.infrastructure.gov.au/media-communications/first-nations-digital-inclusion", "Licence not stated",
     "nt-connectivity-landscape/fn_wifi_funded_projects_2026.csv", ["funded"]),
    ("Geoscape National Roads (Digital Atlas of Australia)", "Geoscape Australia via Geoscience Australia",
     "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/National_Roads/FeatureServer/0", "CC BY 4.0",
     "nt-context-data/nt_national_roads_geoscape.geojson", ["places", "sites"]),
    ("NTLIS land council boundaries", "Northern Territory Government (NTLIS)",
     "https://ogc.ntlis.nt.gov.au/gs/ntlis/wfs", "CC BY 4.0 (to confirm)",
     "nt-context-data/ntlis_wfs/LAND_COUNCIL_BOUNDARIES.geojson", ["places"]),
    ("NTLIS counter disaster areas", "Northern Territory Government (NTLIS)",
     "https://ogc.ntlis.nt.gov.au/gs/ntlis/wfs", "CC BY 4.0 (to confirm)",
     "nt-context-data/ntlis_wfs/COUNTER_DISASTER_AREAS.geojson", ["places"]),
    ("NTG bushfire risk for remote communities 2020", "Bushfires NT, Northern Territory Government",
     "https://data.nt.gov.au/dataset/bushfire-risk-for-remote-communities-in-the-northern-territory", "CC BY 4.0",
     "nt-context-data/nt_remote_communities_bushfire_risk_2020.csv", ["places"]),
    ("nbn outage register", "NBN Co",
     "https://www.nbnco.com.au/content/dam/nbnco/acma-content/nbn_outage_register.csv", "Terms not stated",
     "nt-connectivity-landscape/nbn_outage_register.csv", ["outage_ledger"]),
    ("National Audit of Mobile Coverage non-alignment data, September 2026", _DITRDCSA,
     "https://www.infrastructure.gov.au/sites/default/files/documents/national_audit_of_mobile_coverage_non-alignment_data_september_2026.csv",
     "Licence to confirm", "listed-datasets/fnmap/namc_nonalign_NT.csv", ["namc_tiles"]),
]


def _md5(path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _rows(table: str) -> int:
    p = PROCESSED / f"{table}.csv"
    return int(len(pd.read_csv(p, low_memory=False))) if p.exists() else 0


def _previous_md5() -> dict:
    """Keep hashes from an earlier run when the raw files are not on this machine."""
    if not OUT.exists():
        return {}
    old = pd.read_csv(OUT, dtype=str).fillna("")
    return dict(zip(old.raw_path, old.raw_md5))


def build() -> list[dict]:
    prev = _previous_md5()
    rows = []
    for source, publisher, url, licence, rel, tables in SOURCES:
        raw = RAW / rel
        raw_path = f"data_probe/{rel}"
        md5 = _md5(raw) if raw.exists() else prev.get(raw_path, "")
        rows.append({"source": source, "publisher": publisher, "url": url, "licence": licence,
                     "retrieved": RETRIEVED, "raw_path": raw_path, "raw_md5": md5,
                     "processed_table": ";".join(tables),
                     "processed_rows": ";".join(str(_rows(t)) for t in tables)})
    return rows


def write() -> list[dict]:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = write()
    have = sum(1 for r in rows if r["raw_md5"])
    print(f"{len(rows)} rows written to {OUT} ({have} with an md5)")
