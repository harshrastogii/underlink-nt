"""NT coastline for the web app's hero map (web/data/nt_coast.js).

The land council boundaries in nt_base.js run across the sea channels, so the Tiwi Islands and
Groote Eylandt join the mainland. ABS Remoteness Areas follow the coast, so their union gives the
real outline with its islands. Source: ABS ASGS Edition 3, Remoteness Areas 2021 (CC BY 4.0),
clipped to the NT. Simplified for display; no names.

    python scripts/hero_outline.py
"""
import json
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data_probe" / "nt-context-data" / "nt_remoteness_2021.gpkg"
OUT = ROOT / "web" / "data" / "nt_coast.js"


def main() -> None:
    nt = gpd.read_file(SRC).to_crs("EPSG:4326").union_all().simplify(0.012, preserve_topology=True)
    rings = [[[round(x, 3), round(y, 3)] for x, y in g.exterior.coords]
             for g in sorted(getattr(nt, "geoms", [nt]), key=lambda g: -g.area) if g.area > 0.004]
    OUT.write_text("// NT coastline with islands, from ABS ASGS Remoteness Areas 2021 (CC BY 4.0), simplified, no names.\n"
                   "window.NT_COAST = " + json.dumps(rings, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rings)} rings, {sum(map(len, rings))} points, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
