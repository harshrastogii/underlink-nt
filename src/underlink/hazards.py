"""Cyclone tracks as lines, and which relays and places sit near them."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString, Point

from .config import P, PROCESSED

ALBERS = P["geometry"]["crs_metric"]
GALE = P["hazards"]["gale_threshold_ms"]


def load_tracks() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "tracks.csv", parse_dates=["time"])


def track_geometry(fixes: pd.DataFrame, cyclone_only: bool = False):
    """Join the 6-hourly fixes of one system into a line in metres (EPSG:3577).

    The default "system track" keeps every fix, including the tropical low and
    ex-cyclone stages: sustained cloud over solar sites (Ex-TC Megan, 2024) is
    one of the ways towers go down. `cyclone_only` keeps only segments where
    either end is at gale strength or more, as a stricter sensitivity case.
    """
    g = gpd.GeoSeries(gpd.points_from_xy(fixes.lon, fixes.lat), crs="EPSG:4326").to_crs(ALBERS)
    pts = list(g)
    if len(pts) == 1:
        return pts[0]
    if not cyclone_only:
        return LineString(pts)
    w = fixes.max_wind_ms.fillna(0).values
    segs = [LineString([pts[i], pts[i + 1]]) for i in range(len(pts) - 1) if max(w[i], w[i + 1]) >= GALE]
    return MultiLineString(segs) if segs else None


def to_metric_points(df: pd.DataFrame) -> gpd.GeoSeries:
    return gpd.GeoSeries(gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326").to_crs(ALBERS)


def within(points: gpd.GeoSeries, geom, km: float):
    """Boolean mask: which points lie within km of the track geometry."""
    if geom is None:
        return pd.Series(False, index=points.index)
    return points.distance(geom) <= km * 1000


def exposure_counts(points: gpd.GeoSeries, tracks: pd.DataFrame, km: float) -> pd.Series:
    """Number of distinct systems whose track came within km of each point."""
    counts = pd.Series(0, index=points.index)
    for _, fixes in tracks.groupby("event_id"):
        counts += within(points, track_geometry(fixes), km).astype(int)
    return counts
