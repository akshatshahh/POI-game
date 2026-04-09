"""Geographic study regions for the POI game (WGS84)."""

# Greater Los Angeles — Overture / game default study area (approx. LA County core + metro)
# lon_min, lat_min, lon_max, lat_max
LOS_ANGELES_BBOX: tuple[float, float, float, float] = (
    -118.67,  # west
    33.70,  # south
    -118.08,  # east
    34.34,  # north
)


def point_in_los_angeles(lat: float, lon: float) -> bool:
    lon_min, lat_min, lon_max, lat_max = LOS_ANGELES_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
