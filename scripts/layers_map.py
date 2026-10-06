"""Figure I1 (report Appendix I; the caption there carries the source credits): STAND satellite sites and published 1% AEP flood studies on the
Geoscience Australia National Base Map, with an inset of the Katherine River flood study.

    python scripts/layers_map.py        # writes outputs/public/figures/layers_map.jpg

Layers come from web/data/nt_base.js (written by scripts/hazards_snapshot.py --base), so the figure
needs no restricted data and shows no relay, site key or community result. The base map is fetched
from Geoscience Australia's ArcGIS export service (CC BY 4.0); without internet the NT outline is
drawn instead.
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = ["Arial", "Helvetica", "DejaVu Sans"]
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "public" / "figures" / "layers_map.jpg"   # JPEG keeps the submission ZIP under the 10 MB upload limit
GA = "https://services.ga.gov.au/gis/rest/services/NationalBaseMap/MapServer/export"
NAVY, FLOOD, STAND = "#16325C", "#2F6DB5", "#0E8FA8"
NT_BOX = (128.8, -26.2, 138.2, -10.7)
INSET_BOX = (132.10, -14.62, 132.48, -14.33)          # Katherine River flood study (2025)


def base_layers() -> dict:
    s = (ROOT / "web" / "data" / "nt_base.js").read_text()
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


def ga_image(box, px):
    """Base map image and its extent in EPSG:3857, or None when offline."""
    b = gpd.GeoSeries([Point(box[0], box[1]), Point(box[2], box[3])], crs=4326).to_crs(3857)
    x0, y0, x1, y1 = b.x[0], b.y[0], b.x[1], b.y[1]
    w = px; h = int(px * (y1 - y0) / (x1 - x0))
    url = (f"{GA}?bbox={x0},{y0},{x1},{y1}&bboxSR=3857&imageSR=3857&size={w},{h}&format=png&transparent=false&f=image")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return plt.imread(io.BytesIO(r.read()), format="png"), (x0, x1, y0, y1)
    except Exception:
        return None, (x0, x1, y0, y1)


def main() -> None:
    B = base_layers()
    flood = gpd.GeoSeries([Polygon([(x, y) for x, y in ring]) for ring in B["flood"]], crs=4326).to_crs(3857)
    stand = gpd.GeoSeries([Point(x, y) for x, y in B["stand"]], crs=4326).to_crs(3857)
    outline = gpd.GeoSeries([Polygon(r) for r in B["outline"]], crs=4326).to_crs(3857)

    fig = plt.figure(figsize=(8.6, 7.6), dpi=200)
    ax = fig.add_axes([0.0, 0.0, 0.62, 1.0])
    img, ext = ga_image(NT_BOX, 1400)
    if img is not None:
        ax.imshow(img, extent=ext, origin="upper", zorder=0)
    else:
        outline.plot(ax=ax, color="#EEF3F9", edgecolor=NAVY, linewidth=0.8, zorder=0)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    flood.plot(ax=ax, color=FLOOD, alpha=0.55, edgecolor=FLOOD, linewidth=0.6, zorder=2)
    # flood study areas are small at this scale: ring each study (fragments within 40 km merged) so it can be found
    for g in gpd.GeoSeries(flood.centroid.buffer(40000).union_all(), crs=3857).explode(index_parts=False):
        c = g.centroid
        ax.add_patch(plt.Circle((c.x, c.y), 30000, fill=False, edgecolor=FLOOD, linewidth=1.2, zorder=3))
    stand.plot(ax=ax, marker="s", markersize=14, color=STAND, edgecolor="white", linewidth=0.5, zorder=4)
    ax.set_axis_off()

    # inset: one flood study at a scale where its shape shows
    ib = gpd.GeoSeries([Point(INSET_BOX[0], INSET_BOX[1]), Point(INSET_BOX[2], INSET_BOX[3])], crs=4326).to_crs(3857)
    ax.add_patch(Rectangle((ib.x[0], ib.y[0]), ib.x[1] - ib.x[0], ib.y[1] - ib.y[0], fill=False, edgecolor=NAVY, linewidth=1, zorder=5))
    ia = fig.add_axes([0.63, 0.50, 0.37, 0.44])
    iimg, iext = ga_image(INSET_BOX, 700)
    if iimg is not None:
        ia.imshow(iimg, extent=iext, origin="upper", zorder=0)
    raw = ROOT / "data_probe" / "nt-context-data" / "ntlis_wfs" / "NTPS_SUBJECT_TO_FLOODING.geojson"
    detail = gpd.read_file(raw).to_crs(3857) if raw.exists() else gpd.GeoDataFrame(geometry=flood)
    detail.plot(ax=ia, color=FLOOD, alpha=0.5, edgecolor=FLOOD, linewidth=0.4, zorder=2)
    ia.set_xlim(iext[0], iext[1]); ia.set_ylim(iext[2], iext[3])
    ia.set_xticks([]); ia.set_yticks([]); ia.set_xlabel(""); ia.set_ylabel("")
    for s in ia.spines.values():
        s.set_edgecolor(NAVY); s.set_linewidth(1)
    ia.set_title("Inset: Katherine River flood study (2025)", fontsize=11, color=NAVY, pad=5)

    handles = [Patch(facecolor=FLOOD, alpha=0.55, edgecolor=FLOOD, label="Published 1% AEP flood study\n(ringed on the NT map)"),
               Line2D([], [], marker="s", linestyle="", markersize=6, markerfacecolor=STAND, markeredgecolor="white",
                      label="STAND satellite site")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.625, 0.43), bbox_transform=fig.transFigure, fontsize=11, frameon=True, facecolor="white", edgecolor="#D6DEE8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", pad_inches=0.04, pil_kwargs={"quality": 90, "subsampling": 0})
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
