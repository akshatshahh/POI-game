"""Shared Overture Maps ingestion helpers for the data scripts.

Both seed_production_data.py and load_overture_places.py fetch places from
the Overture S3 parquet release and upsert them into the Postgres `places`
table; this module holds that logic so the release pin and the upsert SQL
live in exactly one place.

Overture Places taxonomy (2026-06-17+):
  - basic_category: cognitively basic display label (~280 values)
  - taxonomy.primary / hierarchy / alternates: full tree for aggregation
  - categories: legacy primary/alternate (deprecated; kept for compatibility)
"""

import json
import logging

log = logging.getLogger(__name__)

# Pinned Overture Maps release. Available releases are listed at
# https://docs.overturemaps.org/release/ — bump this to upgrade.
# 2026-06-17.0 includes basic_category + taxonomy (categories still present).
OVERTURE_RELEASE = "2026-06-17.0"
OVERTURE_PLACES_PATH = (
    f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}/theme=places/type=place/*"
)


def connect_postgres():
    """Open a synchronous psycopg2 connection using the app's DATABASE_URL."""
    import psycopg2

    from app.config import settings

    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


def _as_str_list(value) -> list[str] | None:
    """Normalize a DuckDB/Python list-like value into a list of strings."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value] if value else None
    if not isinstance(value, (list, tuple)):
        return None
    out = [str(x) for x in value if x is not None and str(x).strip()]
    return out or None


def _unpack_taxonomy(taxonomy_raw) -> tuple[str | None, list[str] | None, list[str] | None]:
    """Return (primary, hierarchy, alternates) from an Overture taxonomy struct."""
    if taxonomy_raw is None:
        return None, None, None
    if isinstance(taxonomy_raw, str):
        try:
            taxonomy_raw = json.loads(taxonomy_raw)
        except (json.JSONDecodeError, TypeError):
            return None, None, None
    if not isinstance(taxonomy_raw, dict):
        return None, None, None

    primary = taxonomy_raw.get("primary")
    hierarchy = _as_str_list(taxonomy_raw.get("hierarchy"))
    # Schema field is "alternates"; some older docs say "alternate".
    alternates = _as_str_list(
        taxonomy_raw.get("alternates", taxonomy_raw.get("alternate"))
    )
    return (
        str(primary) if primary else None,
        hierarchy,
        alternates,
    )


def fetch_overture_places(bbox: tuple[float, float, float, float]) -> list[tuple]:
    """Pull real POIs from Overture Maps S3 via DuckDB.

    bbox is (lon_min, lat_min, lon_max, lat_max). Returns rows of
    (id, names, categories, basic_category, taxonomy, lat, lon, wkt).
    """
    import duckdb

    lon_min, lat_min, lon_max, lat_max = bbox
    log.info(
        "Connecting to Overture Maps S3 release %s (bbox: %.4f,%.4f -> %.4f,%.4f)",
        OVERTURE_RELEASE, lon_min, lat_min, lon_max, lat_max,
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
        basic_category,
        taxonomy,
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
    """Create the places table if missing and add taxonomy columns if needed."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id TEXT PRIMARY KEY,
            names JSONB,
            categories JSONB,
            basic_category TEXT,
            taxonomy_primary TEXT,
            taxonomy_hierarchy TEXT[],
            taxonomy_alternate TEXT[],
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            geometry GEOMETRY(GEOMETRY, 4326)
        )
    """)
    # Older local DBs may predate taxonomy / lat-lon columns.
    for ddl in (
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION",
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS basic_category TEXT",
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS taxonomy_primary TEXT",
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS taxonomy_hierarchy TEXT[]",
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS taxonomy_alternate TEXT[]",
    ):
        cur.execute(ddl)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_places_latlon ON places (lat, lon)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_basic_category ON places (basic_category)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_taxonomy_primary ON places (taxonomy_primary)"
    )
    conn.commit()
    cur.close()


def upsert_places(conn, rows: list[tuple], batch_size: int = 500) -> int:
    """Upsert Overture rows into the places table (keeps legacy categories).

    Rows are sent in batches of batch_size per statement: one round-trip per
    batch instead of per row, which is the difference between minutes and
    hours when the database is remote (e.g. Neon).
    """
    from psycopg2.extras import execute_values

    ensure_places_table(conn)
    cur = conn.cursor()

    values = []
    for row in rows:
        # Support both old 6-tuples and new 8-tuples during transition.
        if len(row) == 6:
            pid, names_raw, cats_raw, lat, lon, wkt = row
            basic_category = None
            taxonomy_raw = None
        else:
            pid, names_raw, cats_raw, basic_category, taxonomy_raw, lat, lon, wkt = row

        tax_primary, tax_hierarchy, tax_alternate = _unpack_taxonomy(taxonomy_raw)
        if basic_category is not None:
            basic_category = str(basic_category)

        names_json = json.dumps(names_raw) if names_raw is not None else None
        cats_json = json.dumps(cats_raw) if cats_raw is not None else None

        values.append((
            pid, names_json, cats_json,
            basic_category, tax_primary, tax_hierarchy, tax_alternate,
            lat, lon, wkt,
        ))

    inserted = 0
    for start in range(0, len(values), batch_size):
        batch = values[start:start + batch_size]
        execute_values(
            cur,
            """
            INSERT INTO places (
                id, names, categories,
                basic_category, taxonomy_primary, taxonomy_hierarchy, taxonomy_alternate,
                lat, lon, geometry
            )
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                names = EXCLUDED.names,
                categories = EXCLUDED.categories,
                basic_category = EXCLUDED.basic_category,
                taxonomy_primary = EXCLUDED.taxonomy_primary,
                taxonomy_hierarchy = EXCLUDED.taxonomy_hierarchy,
                taxonomy_alternate = EXCLUDED.taxonomy_alternate,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                geometry = EXCLUDED.geometry
            """,
            batch,
            template=(
                "(%s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, "
                "ST_GeomFromText(%s, 4326))"
            ),
        )
        inserted += len(batch)
        if inserted % 25_000 < batch_size:
            log.info("Upserted %d / %d places...", inserted, len(values))

    conn.commit()
    cur.close()
    log.info("Upserted %d places into Postgres", inserted)
    return inserted
