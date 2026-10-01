"""Build data_probe/listed-datasets/acma/nt_p2p_links.csv from the ACMA RRL bulk tables.

The RRL bulk download (https://www.acma.gov.au/radiocomms-licence-data, spectra_rrl.zip) has
one row per device. Each transmitter names its receiver through RELATED_EFL_ID (the receiver
device's EFL_ID), and the receiver's SITE_ID is the far end of the link.

    python scripts/extract_acma.py            # writes nt_p2p_links.csv next to the raw tables
    python scripts/extract_acma.py --check    # compares with the existing file instead

Then `python run_all.py --prepare` rebuilds data/processed from it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ACMA = ROOT / "data_probe" / "listed-datasets" / "acma"
OUT = ACMA / "nt_p2p_links.csv"
BANDS = [(0, 1, "<1GHz"), (1, 3, "1-3"), (3, 5, "3-5"), (5, 9, "5-9 (long-haul MW)"), (9, 12, "9-12"),
         (12, 16, "12-16"), (16, 20, "16-20"), (20, 30, "20-30"), (30, 1e9, ">30")]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def build() -> pd.DataFrame:
    site = pd.read_csv(ACMA / "site.csv", usecols=["SITE_ID", "LATITUDE", "LONGITUDE", "STATE"], low_memory=False)
    nt_sites = set(site[site.STATE == "NT"].SITE_ID)
    # 1. transmitters at NT sites, plus every device's EFL id so receivers can be found
    #    (the device table is 2 M rows, so read it in chunks)
    parts, efl = [], []
    for ch in pd.read_csv(ACMA / "device_details.csv", low_memory=False, chunksize=250_000):
        parts.append(ch[(ch.DEVICE_TYPE == "T") & ch.SITE_ID.isin(nt_sites)])
        efl.append(ch[["EFL_ID", "SITE_ID", "HEIGHT"]].dropna(subset=["EFL_ID"]))
    dev = pd.concat(parts, ignore_index=True)
    efl = pd.concat(efl, ignore_index=True).drop_duplicates("EFL_ID").set_index("EFL_ID")
    # 2. point-to-point licences and who holds them
    lic = pd.read_csv(ACMA / "licence.csv", low_memory=False,
                      usecols=["LICENCE_NO", "CLIENT_NO", "LICENCE_TYPE_NAME", "LICENCE_CATEGORY_NAME",
                               "DATE_ISSUED", "DATE_OF_EXPIRY", "STATUS_TEXT"])
    lic = lic[lic.LICENCE_CATEGORY_NAME.astype(str).str.startswith("Point to Point")]
    cli = pd.read_csv(ACMA / "client.csv", low_memory=False, usecols=["CLIENT_NO", "LICENCEE", "TRADING_NAME", "CLIENT_TYPE_ID"])
    d = dev.merge(lic, on="LICENCE_NO").merge(cli, on="CLIENT_NO", how="left")
    # 3. receive end: the site of the receiver device each transmitter points to
    #    Receivers outside the NT are left empty: the analysis covers NT links only.
    d["RX_SITE"] = d.RELATED_EFL_ID.map(efl.SITE_ID).where(lambda s: s.isin(nt_sites))
    d["RX_HEIGHT"] = d.RELATED_EFL_ID.map(efl.HEIGHT).where(d.RX_SITE.notna())
    # 4. coordinates, length, frequency band, year
    xy = site.set_index("SITE_ID")[["LATITUDE", "LONGITUDE"]]
    d["tx_lat"], d["tx_lon"] = d.SITE_ID.map(xy.LATITUDE), d.SITE_ID.map(xy.LONGITUDE)
    d["rx_lat"], d["rx_lon"] = d.RX_SITE.map(xy.LATITUDE), d.RX_SITE.map(xy.LONGITUDE)
    d["km"] = haversine_km(d.tx_lat, d.tx_lon, d.rx_lat, d.rx_lon)
    d["GHz"] = d.FREQUENCY / 1e9
    d["band"] = [next((b for lo, hi, b in BANDS if lo <= g < hi), None) for g in d.GHz]
    d["year_issued"] = pd.to_datetime(d.DATE_ISSUED, errors="coerce").dt.year
    return d


def main() -> None:
    d = build()
    if "--check" in sys.argv:
        old = pd.read_csv(OUT, low_memory=False)
        same_rows = set(old.SDD_ID) == set(d.SDD_ID)
        m = old.merge(d[["SDD_ID", "RX_SITE"]], on="SDD_ID", suffixes=("_old", "_new"))
        same_rx = ((m.RX_SITE_old == m.RX_SITE_new) | (m.RX_SITE_old.isna() & m.RX_SITE_new.isna())).mean()
        print(f"rows: existing {len(old)}, rebuilt {len(d)}, same device ids: {same_rows}, same receive site: {same_rx:.1%}")
        return
    cols = list(pd.read_csv(OUT, nrows=0).columns) if OUT.exists() else list(d.columns)
    d[[c for c in cols if c in d.columns]].to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(d)} rows)")


if __name__ == "__main__":
    main()
