"""Shared geospatial helpers used by services, routers, and scripts."""

import math

import h3

from app.config import settings

EARTH_RADIUS_METERS = 6_371_000


def lat_lon_to_h3(lat: float, lon: float) -> str:
    """H3 cell index for a point, at the app-wide dedup resolution."""
    return h3.latlng_to_cell(lat, lon, settings.h3_resolution)


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return EARTH_RADIUS_METERS * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
