"""Service to query nearby POIs from the places table.

Supports two modes:
  - PostGIS mode (local dev with geometry column)
  - Haversine mode (cloud deploy with flat lat/lon columns)

Auto-detects which mode to use based on whether the 'geometry' column exists.
The detection result is cached for the process lifetime, so adding the
geometry column to a running deployment requires a backend restart.
"""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.geo import haversine_meters

_use_postgis: bool | None = None

# Meters per degree of latitude, used to turn a radius into a bounding box.
_METERS_PER_DEGREE = 111_000

# Degrees of longitude shrink with latitude (by cos(lat)); widen the box to
# compensate. 1.5 covers latitudes up to ~48°, fine for the LA study area.
_LON_MARGIN_FACTOR = 1.5


async def _detect_mode(db: AsyncSession) -> bool:
    """Check if the places table has a geometry column (PostGIS)."""
    global _use_postgis
    if _use_postgis is not None:
        return _use_postgis
    result = await db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'places' AND column_name = 'geometry'"
    ))
    _use_postgis = result.first() is not None
    return _use_postgis


async def get_nearby_pois(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_meters: int | None = None,
    max_results: int | None = None,
) -> list[dict]:
    """Find POIs within radius_meters of the given lat/lon."""
    radius = radius_meters or settings.poi_search_radius_meters
    limit = max_results or settings.poi_max_candidates

    use_postgis = await _detect_mode(db)

    if use_postgis:
        return await _query_postgis(db, lat, lon, radius, limit)
    return await _query_haversine(db, lat, lon, radius, limit)


async def _query_postgis(
    db: AsyncSession, lat: float, lon: float, radius: int, limit: int,
) -> list[dict]:
    query = text("""
        SELECT
            id,
            names::text AS names_raw,
            categories::text AS categories_raw,
            ST_Y(ST_Centroid(geometry::geometry)) AS lat,
            ST_X(ST_Centroid(geometry::geometry)) AS lon,
            ST_Distance(
                geometry::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) AS distance_meters
        FROM places
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius
        )
        ORDER BY distance_meters ASC
        LIMIT :limit
    """)
    result = await db.execute(query, {"lat": lat, "lon": lon, "radius": radius, "limit": limit})
    rows = result.mappings().all()
    return [_row_to_poi(row, row["distance_meters"]) for row in rows]


async def _query_haversine(
    db: AsyncSession, lat: float, lon: float, radius: int, limit: int,
) -> list[dict]:
    deg_margin = radius / _METERS_PER_DEGREE * _LON_MARGIN_FACTOR
    query = text("""
        SELECT id, names::text AS names_raw, categories::text AS categories_raw, lat, lon
        FROM places
        WHERE lat BETWEEN :lat_min AND :lat_max
          AND lon BETWEEN :lon_min AND :lon_max
        ORDER BY (lat - :lat) * (lat - :lat) + (lon - :lon) * (lon - :lon) ASC
        LIMIT :prelimit
    """)
    result = await db.execute(query, {
        "lat": lat, "lon": lon,
        "lat_min": lat - deg_margin, "lat_max": lat + deg_margin,
        "lon_min": lon - deg_margin, "lon_max": lon + deg_margin,
        "prelimit": limit * 3,
    })
    rows = result.mappings().all()

    pois = []
    for row in rows:
        dist = haversine_meters(lat, lon, row["lat"], row["lon"])
        if dist <= radius:
            pois.append(_row_to_poi(row, dist))
    pois.sort(key=lambda p: p["distance_meters"])
    return pois[:limit]


def _row_to_poi(row: dict, distance_meters: float) -> dict:
    return {
        "id": str(row["id"]),
        "name": _extract_name(row["names_raw"]),
        "category": extract_category(row["categories_raw"]),
        "lat": row["lat"],
        "lon": row["lon"],
        "distance_meters": round(distance_meters, 1),
    }


def _extract_name(names_raw: str | None) -> str:
    if not names_raw:
        return "Unknown"
    try:
        names = json.loads(names_raw)
        if isinstance(names, dict):
            return names.get("primary", names.get("common", "Unknown"))
        if isinstance(names, list) and names:
            first = names[0]
            if isinstance(first, dict):
                return first.get("value", "Unknown")
            return str(first)
    except (json.JSONDecodeError, TypeError):
        pass
    return str(names_raw)[:100] if names_raw else "Unknown"


def extract_category(categories_raw: str | None) -> str:
    if not categories_raw:
        return "uncategorized"
    try:
        cats = json.loads(categories_raw)
        if isinstance(cats, dict):
            primary = cats.get("primary", cats.get("main"))
            if primary:
                return str(primary)
            alternates = cats.get("alternate", [])
            if alternates:
                return str(alternates[0])
        if isinstance(cats, list) and cats:
            return str(cats[0])
    except (json.JSONDecodeError, TypeError):
        pass
    return "uncategorized"
