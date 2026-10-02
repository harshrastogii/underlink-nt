# Makes data_probe/listed-datasets/accc/nt_communities_telstra4g_outdoor_2026.csv from the ACCC 2026 Telstra 4G outdoor
# KML (https://data.gov.au/data/dataset/accc-mobile-infrastructure-report-data-release).
# Usage: python scripts/kml_nt_clip.py telstra-4g-outdoor-2026.kml nt_communities_telstra4g_outdoor_2026.csv
# Stream-parse a large ACCC coverage KML, keep polygons intersecting the NT bounding box,
# then test NT community points (NTG 2021 gazetteer, 782 places) for coverage.
import sys, re, json, xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point, box, mapping
from shapely.ops import unary_union
from shapely import STRtree
import pandas as pd
kml, out = sys.argv[1], sys.argv[2]
NT = box(129.0, -26.0, 138.0, -10.9)
ns = '{http://www.opengis.net/kml/2.2}'
polys = []
n = 0
def parse_coords(t):
    pts = []
    for tok in t.split():
        a = tok.split(',')
        pts.append((float(a[0]), float(a[1])))
    return pts
for ev, el in ET.iterparse(kml, events=('end',)):
    if el.tag == ns + 'Polygon':
        n += 1
        ob = el.find(f'{ns}outerBoundaryIs/{ns}LinearRing/{ns}coordinates')
        if ob is not None and ob.text:
            ext = parse_coords(ob.text)
            xs = [p[0] for p in ext]; ys = [p[1] for p in ext]
            if max(xs) >= 129 and min(xs) <= 138 and max(ys) >= -26 and min(ys) <= -10.9 and len(ext) >= 4:
                holes = []
                for ib in el.findall(f'{ns}innerBoundaryIs/{ns}LinearRing/{ns}coordinates'):
                    h = parse_coords(ib.text)
                    if len(h) >= 4: holes.append(h)
                p = Polygon(ext, holes)
                if not p.is_valid: p = p.buffer(0)
                polys.append(p)
        el.clear()
    elif el.tag == ns + 'Placemark':
        el.clear()
print('polygons total', n, 'NT-bbox polygons', len(polys), flush=True)
tree = STRtree(polys)
com = pd.read_excel(sys.argv[3], sheet_name='Communities')
res = []
for _, r in com.iterrows():
    pt = Point(float(r.LONGITUDE), float(r.LATITUDE))
    idx = tree.query(pt, predicate='intersects')
    res.append(len(idx) > 0)
com['covered'] = res
com.to_csv(out, index=False)
print('communities', len(com), 'covered', sum(res), flush=True)
print(com.groupby('COMMUNITY_TYPE').covered.agg(['sum', 'count']), flush=True)
# NT covered area: sum of clipped polygon areas (coverage polygons assumed non-overlapping)
from shapely.ops import transform
import pyproj
proj = pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:3577', always_xy=True).transform
clipped = [p.intersection(NT) for p in polys]
area = sum(transform(proj, c).area for c in clipped if not c.is_empty) / 1e6
print('covered area in NT bbox km2 (sum of parts)', round(area), flush=True)
import pickle
pickle.dump([c for c in clipped if not c.is_empty], open(out.replace('.csv', '_nt_polys.pkl'), 'wb'))
