"""Small geometry helpers. Distances are great-circle km unless stated."""
from __future__ import annotations

import numpy as np


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Works on scalars or numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def nearest(lat, lon, lats, lons):
    """Index and distance (km) of the nearest point in (lats, lons) to (lat, lon)."""
    d = haversine_km(lat, lon, np.asarray(lats), np.asarray(lons))
    i = int(np.argmin(d))
    return i, float(d[i])


def count_within(lat, lon, lats, lons, km):
    """How many points lie within km of (lat, lon)."""
    if len(lats) == 0:
        return 0
    return int((haversine_km(lat, lon, np.asarray(lats), np.asarray(lons)) <= km).sum())
