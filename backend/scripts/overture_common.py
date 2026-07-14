"""Shared Overture Maps ingestion helpers for the data scripts.

Both seed_production_data.py and load_overture_places.py fetch places from
the Overture S3 parquet release and upsert them into the Postgres `places`
table; this module holds that logic so the release pin and the upsert SQL
live in exactly one place.
"""

import json
import logging

log = logging.getLogger(__name__)

# Pinned Overture Maps release. Available releases are listed at
# https://docs.overturemaps.org/release/ — bump this to upgrade.
OVERTURE_RELEASE = "2026-02-18.0"
OVERTURE_PLACES_PATH = (
    f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}/theme=places/type=place/*"
)


def connect_postgres():
    """Open a synchronous psycopg2 connection using the app's DATABASE_URL."""
    import psycopg2

    from app.config import settings

    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


def fetch_overture_places(bbox: tuple[float, float, float, float]) -> list[tuple]:
    """Pull real POIs from Overture Maps S3 via DuckDB.

    bbox is (lon_min, lat_min, lon_max, lat_max). Returns rows of
    (id, names, categories, lat, lon, wkt).
    """
    import duckdb

    lon_min, lat_min, lon_max, lat_max = bbox
    log.info(
        "Connecting to Overture Maps S3 (bbox: %.4f,%.4f -> %.4f,%.4f)",
        lon_min, lat_min, lon_max, lat_max,
    )

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-west-2';")

    query = f"""
    SELECT
        id,
        names,
        categories,
        ST_Y(ST_Centroid(geometry)) AS lat,
        ST_X(ST_Centroid(geometry)) AS lon,
        ST_AsText(geometry) AS wkt
    FROM read_parquet('{OVERTURE_PLACES_PATH}')
    WHERE bbox.xmin >= {lon_min}
      AND bbox.xmax <= {lon_max}
      AND bbox.ymin >= {lat_min}
      AND bbox.ymax <= {lat_max}
    """

    log.info("Querying Overture S3 parquet — this may take 1-3 minutes...")
    rows = con.execute(query).fetchall()
    log.info("Fetched %d raw places from Overture", len(rows))
    con.close()
    return rows


def ensure_places_table(conn) -> None:
    """Create the places table if missing (requires PostGIS for geometry)."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id TEXT PRIMARY KEY,
            names JSONB,
            categories JSONB,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            geometry GEOMETRY(GEOMETRY, 4326)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_places_latlon ON places (lat, lon)")
    conn.commit()
    cur.close()


def upsert_places(conn, rows: list[tuple]) -> int:
    """Upsert Overture rows into the places table.

    Adds lat/lon columns to older tables that predate them, so deployments
    without PostGIS can use the Haversine query fallback.
    """
    cur = conn.cursor()

    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'places' AND column_name = 'lat'"
    )
    has_latlon = cur.fetchone() is not None

    if not has_latlon:
        log.info("Adding lat/lon columns to places table for Haversine fallback")
        cur.execute("ALTER TABLE places ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION")
        cur.execute("ALTER TABLE places ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_places_latlon ON places (lat, lon)")
        conn.commit()

    inserted = 0
    for row in rows:
        pid, names_raw, cats_raw, lat, lon, wkt = row
        names_json = json.dumps(names_raw) if names_raw else None
        cats_json = json.dumps(cats_raw) if cats_raw else None

        cur.execute("""
            INSERT INTO places (id, names, categories, lat, lon, geometry)
            VALUES (%s, %s::jsonb, %s::jsonb, %s, %s, ST_GeomFromText(%s, 4326))
            ON CONFLICT (id) DO UPDATE SET
                names = EXCLUDED.names,
                categories = EXCLUDED.categories,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                geometry = EXCLUDED.geometry
        """, (pid, names_json, cats_json, lat, lon, wkt))
        inserted += 1

    conn.commit()
    cur.close()
    log.info("Upserted %d places into Postgres", inserted)
    return inserted
