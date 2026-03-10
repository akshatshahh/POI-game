"""Service to query nearby POIs from the places table.

Supports two modes:
  - PostGIS mode (local dev with geometry column)
  - Haversine mode (cloud deploy with flat lat/lon columns)

Auto-detects which mode to use based on whether the 'geometry' column exists.
"""

import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

_use_postgis: bool | None = None


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


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
    return [_row_to_poi(row, postgis=True) for row in rows]


async def _query_haversine(
    db: AsyncSession, lat: float, lon: float, radius: int, limit: int,
) -> list[dict]:
    deg_margin = radius / 111_000 * 1.5
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
        dist = _haversine(lat, lon, row["lat"], row["lon"])
        if dist <= radius:
            pois.append({
                "id": str(row["id"]),
                "name": _extract_name(row["names_raw"]),
                "category": _extract_category(row["categories_raw"]),
                "lat": row["lat"],
                "lon": row["lon"],
                "distance_meters": round(dist, 1),
            })
    pois.sort(key=lambda p: p["distance_meters"])
    return pois[:limit]


def _row_to_poi(row: dict, postgis: bool = False) -> dict:
    return {
        "id": str(row["id"]),
        "name": _extract_name(row["names_raw"]),
        "category": _extract_category(row["categories_raw"]),
        "lat": row["lat"],
        "lon": row["lon"],
        "distance_meters": round(row["distance_meters"], 1) if postgis else 0.0,
    }


def _extract_name(names_raw: str | None) -> str:
    if not names_raw:
        return "Unknown"
    import json
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


def _extract_category(categories_raw: str | None) -> str:
    if not categories_raw:
        return "uncategorized"
    import json
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
