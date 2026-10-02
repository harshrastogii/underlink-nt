"""Snapshot of public hazard feeds for the web app's hazard map (web/data/hazards.js).

    python scripts/hazards_snapshot.py          # fetch the three live feeds (run by a GitHub Action)
    python scripts/hazards_snapshot.py --base   # also rebuild the base map (needs data_probe/)

Feeds (all public, no key):
  - DEA Hotspots, Geoscience Australia: satellite fire hotspots in the last three days
  - NT Road Report, NT Government: current road closures, damage, flooding and roadworks
  - Bureau of Meteorology: current NT warnings (flood, fire weather, severe weather, cyclone)

The browser cannot call these feeds directly (they send no CORS headers), and a snapshot
also keeps working offline, so the site reads a file this script writes. Nothing here
locates a relay, a site or a community.
"""
from __future__ import annotations

import ftplib
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "data" / "hazards.js"
BASE = ROOT / "web" / "data" / "nt_base.js"
NT_BBOX = (129.0, -26.0, 138.0, -10.9)          # lon/lat box around the NT
UA = {"User-Agent": "Underlink hazard snapshot (CDU IT Code Fair 2026)"}


def get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def hotspots() -> list[dict]:
    url = ("https://hotspots.dea.ga.gov.au/geoserver/public/wfs?service=WFS&version=1.1.0&request=GetFeature"
           "&typeName=public:hotspots_three_days&outputFormat=application/json"
           f"&bbox={NT_BBOX[0]},{NT_BBOX[1]},{NT_BBOX[2]},{NT_BBOX[3]},EPSG:4326")
    feats = get_json(url).get("features", [])
    # Geostationary satellites rescan every 10 minutes, so one fire gives many detections.
    # Group them into 0.05-degree cells (about 5 km): one point per cell, with a count and the latest time.
    cells: dict[tuple, dict] = {}
    for f in feats:
        lon, lat = f["geometry"]["coordinates"][:2]
        t = (f.get("properties", {}).get("start_dt") or "")[:16]
        k = (round(lon * 20) / 20, round(lat * 20) / 20)
        c = cells.setdefault(k, {"lon": k[0], "lat": k[1], "n": 0, "latest": ""})
        c["n"] += 1
        c["latest"] = max(c["latest"], t)
    return sorted(cells.values(), key=lambda c: c["latest"], reverse=True)


ROAD_KIND = [("Flooding", "flood"), ("Road Closed", "closed"), ("Closed", "closed"), ("Road Damage", "damage"),
             ("Roadworks", "works"), ("Smoke", "smoke")]


def roads() -> list[dict]:
    rows = get_json("https://roadreport.nt.gov.au/api/Obstruction/GetAll").get("response", [])
    out = []
    for r in rows:
        if r.get("status") != "CURRENT" or not r.get("startPoint"):
            continue
        text = f"{r.get('obstructionType') or ''} {r.get('restrictionType') or ''}"
        kind = next((k for key, k in ROAD_KIND if key.lower() in text.lower()), "other")
        (lat1, lon1), (lat2, lon2) = r["startPoint"], (r.get("endPoint") or r["startPoint"])
        # road names are left out: some match community names, and the public site names no community
        out.append({"kind": kind, "what": r.get("obstructionType") or "", "restriction": r.get("restrictionType") or "",
                    "from": [round(lon1, 3), round(lat1, 3)], "to": [round(lon2, 3), round(lat2, 3)]})
    return out


def warnings() -> list[dict]:
    """Current NT warnings from the BoM FTP feed. Each product's .amoc.xml says whether it is a warning."""
    ftp = ftplib.FTP("ftp.bom.gov.au", timeout=40)
    ftp.login()
    ftp.cwd("/anon/gen/fwo")
    names = [n for n in ftp.nlst() if re.match(r"IDD\d+\.amoc\.xml$", n)]
    out = []
    for n in names:
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {n}", buf.write)
        x = ET.fromstring(buf.getvalue())
        if (x.findtext("product-type") or "") != "W":
            continue
        pid = x.findtext("identifier") or n.split(".")[0]
        title = ""
        try:                                                     # the product's own XML carries its headline
            body = io.BytesIO()
            ftp.retrbinary(f"RETR {pid}.xml", body.write)
            t = ET.fromstring(body.getvalue())
            title = (t.findtext(".//warning-info/title") or t.findtext(".//text[@type='warning_title']")
                     or t.findtext(".//headline") or "").strip()
        except Exception:
            pass
        out.append({"id": pid, "service": x.findtext("service") or "", "title": title or pid,
                    "issued": x.findtext("issue-time-local") or "", "expires": x.findtext("expiry-time") or "",
                    "url": f"https://www.bom.gov.au/products/{pid}.shtml"})
    ftp.quit()
    return out


def base() -> None:
    """NT outline and highways, simplified, for drawing the map with no tiles (works offline)."""
    import geopandas as gpd
    raw = ROOT / "data_probe" / "nt-context-data"
    lc = gpd.read_file(raw / "ntlis_wfs" / "LAND_COUNCIL_BOUNDARIES.geojson").to_crs("EPSG:4326")
    nt = lc.union_all().simplify(0.02)
    rings = []
    for g in (getattr(nt, "geoms", None) or [nt]):
        if g.area > 0.02:
            rings.append([[round(x, 3), round(y, 3)] for x, y in g.exterior.coords])
    rd = gpd.read_file(raw / "nt_national_roads_geoscape.geojson")
    hw = rd[rd.hierarchy == "NATIONAL OR STATE HIGHWAY"].to_crs("EPSG:4326")
    lines = []
    for g in hw.geometry.simplify(0.01):
        for part in (getattr(g, "geoms", None) or [g]):
            lines.append([[round(x, 3), round(y, 3)] for x, y in part.coords])
    # Published 1% AEP flood study areas (NT Planning Scheme overlay, NTLIS), simplified for display only;
    # study names are left out because several name a community.
    fl = gpd.read_file(raw / "ntlis_wfs" / "NTPS_SUBJECT_TO_FLOODING.geojson").to_crs("EPSG:4326")
    flood = []
    for g in fl.geometry.simplify(0.002):
        for part in (getattr(g, "geoms", None) or [g]):
            if part.area > 2e-6:
                flood.append([[round(x, 3), round(y, 3)] for x, y in part.exterior.coords])
    # STAND satellite sites (evacuation centres, fire depots): positions only, rounded to 0.01 degrees, no names.
    import pandas as pd
    st = pd.read_csv(ROOT / "data_probe" / "au-telecom-infra" / "stand" / "stand_skymuster_nt.csv").dropna(subset=["lat", "lon"])
    stand = sorted({(round(r.lon, 2), round(r.lat, 2)) for r in st.itertuples()})
    BASE.write_text("// NT outline (NTLIS land council boundaries), highways (Geoscape National Roads), 1% AEP flood study areas\n"
                    "// (NT Planning Scheme overlay, NTLIS) and STAND satellite sites (DITRDCSA), simplified, no names.\n"
                    "window.NT_BASE = " + json.dumps({"outline": rings, "highways": lines, "flood": flood, "stand": [list(p) for p in stand]},
                                                     separators=(",", ":")) + ";\n")
    print(f"wrote {BASE.relative_to(ROOT)} ({BASE.stat().st_size / 1024:.0f} KB)")


def main() -> None:
    if "--base" in sys.argv:
        base()
    data, errors = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes")}, {}
    for name, fn in (("hotspots", hotspots), ("roads", roads), ("warnings", warnings)):
        try:
            data[name] = fn()
        except Exception as e:                                  # one dead feed must not blank the others
            data[name], errors[name] = [], f"{type(e).__name__}: {e}"[:200]
    data["errors"] = errors
    OUT.write_text("// Generated by scripts/hazards_snapshot.py. Do not edit.\nwindow.HAZARDS = "
                   + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['hotspots'])} hotspots, {len(data['roads'])} road items, "
          f"{len(data['warnings'])} warnings; errors: {errors or 'none'}")


if __name__ == "__main__":
    main()
