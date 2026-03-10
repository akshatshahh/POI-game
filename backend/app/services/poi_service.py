"""Service to query nearby POIs from the Overture Maps Places table using PostGIS."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


async def get_nearby_pois(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_meters: int | None = None,
    max_results: int | None = None,
) -> list[dict]:
    """Find POIs within radius_meters of the given lat/lon.

    Queries the pre-imported Overture Maps 'places' table using PostGIS
    ST_DWithin for efficient spatial filtering. Returns results sorted
    by distance ascending.

    The query adapts to whatever geometry column and attribute columns
    exist in the places table. It expects at minimum: id, geometry (or geom),
    and names (JSONB with 'primary' key) or a name text column.
    """
    radius = radius_meters or settings.poi_search_radius_meters
    limit = max_results or settings.poi_max_candidates

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

    result = await db.execute(
        query,
        {"lat": lat, "lon": lon, "radius": radius, "limit": limit},
    )
    rows = result.mappings().all()

    pois = []
    for row in rows:
        name = _extract_name(row["names_raw"])
        category = _extract_category(row["categories_raw"])
        pois.append({
            "id": str(row["id"]),
            "name": name,
            "category": category,
            "lat": row["lat"],
            "lon": row["lon"],
            "distance_meters": round(row["distance_meters"], 1),
        })

    return pois


def _extract_name(names_raw: str | None) -> str:
    """Extract a display name from the Overture names JSONB field."""
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
    """Extract a display category from the Overture categories JSONB field."""
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
