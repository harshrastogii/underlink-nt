# Makes data_probe/nt-context-data/nt_national_roads_geoscape.geojson. Source and licence: data/manifest.csv.
# Page through Digital Atlas of Australia 'National Roads' (Geoscape) hosted feature layer, NT only.
import json, os, urllib.parse, time, requests
D = os.path.dirname(os.path.abspath(__file__))
B = 'https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/National_Roads/FeatureServer/0/query'
fields = 'road_id,full_street_name,hierarchy,surface,trafficability,status,jurisdiction_control,national_route,state_route'
feats = []; offset = 0
while True:
    q = urllib.parse.urlencode({'where': "state='NT'", 'outFields': fields, 'outSR': 4326, 'geometryPrecision': 5,
                                'resultOffset': offset, 'resultRecordCount': 2000, 'orderByFields': 'OBJECTID', 'f': 'geojson'})
    d = requests.get(B + '?' + q, timeout=120).json()
    fs = d.get('features', [])
    feats += fs; offset += len(fs)
    print(offset, flush=True)
    if len(fs) < 2000: break
    time.sleep(0.3)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(D, 'nt_national_roads_geoscape.geojson'), 'w'))
print('DONE', len(feats))
