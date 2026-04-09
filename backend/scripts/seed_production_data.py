#!/usr/bin/env python3
"""Seed the database with real Overture Maps POIs and realistic GPS visit points.

This is the canonical data pipeline for the POI game. It:
  1. Queries Overture Maps S3 parquet (via DuckDB) for real places around USC.
  2. Upserts them into the local Postgres `places` table.
  3. Generates GPS "visit" points by sampling real POI locations with
     GPS-realistic jitter and time-of-day distributions.
  4. Computes H3 cell IDs for each GPS point.
  5. Cleans up old hand-crafted seed data.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/seed_production_data.py
    python scripts/seed_production_data.py --bbox "-118.30,34.01,-118.27,34.04"
    python scripts/seed_production_data.py --gps-count 50
"""

import argparse
import datetime
import json
import logging
import math
import os
import random
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# USC campus + surrounding neighborhood
DEFAULT_BBOX = (-118.300, 34.010, -118.270, 34.040)

# Time-of-day distributions per category bucket (hour weights)
# Reflects real-world visitation patterns
VISIT_PROFILES = {
    "food": {7: 2, 8: 3, 11: 5, 12: 8, 13: 7, 17: 4, 18: 6, 19: 7, 20: 5, 21: 3},
    "coffee": {6: 3, 7: 6, 8: 8, 9: 5, 10: 3, 14: 4, 15: 3},
    "education": {8: 5, 9: 7, 10: 8, 11: 6, 13: 7, 14: 8, 15: 6, 16: 4},
    "retail": {10: 3, 11: 5, 12: 6, 13: 5, 14: 6, 15: 7, 16: 6, 17: 5, 18: 4},
    "health": {8: 4, 9: 7, 10: 8, 11: 6, 13: 5, 14: 7, 15: 6, 16: 3},
    "nightlife": {18: 2, 19: 3, 20: 5, 21: 7, 22: 8, 23: 6},
    "transit": {7: 5, 8: 8, 9: 4, 16: 4, 17: 7, 18: 8, 19: 3},
    "default": {9: 3, 10: 5, 11: 5, 12: 6, 13: 5, 14: 6, 15: 5, 16: 4, 17: 3},
}

CATEGORY_TO_PROFILE = {
    "restaurant": "food", "fast_food": "food", "food_court": "food",
    "cafe": "coffee", "coffee_shop": "coffee",
    "bar": "nightlife", "pub": "nightlife", "nightclub": "nightlife",
    "university": "education", "school": "education", "college": "education",
    "library": "education",
    "hospital": "health", "clinic": "health", "dentist": "health",
    "doctor": "health", "pharmacy": "health",
    "bus_station": "transit", "train_station": "transit",
    "subway_station": "transit",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--bbox", type=str, default=None,
                    help="lon_min,lat_min,lon_max,lat_max")
    p.add_argument("--gps-count", type=int, default=40,
                    help="Number of GPS visit points to generate")
    p.add_argument("--keep-old", action="store_true",
                    help="Keep old hand-crafted seed data")
    return p.parse_args()


def get_bbox(args):
    if args.bbox:
        return tuple(float(x) for x in args.bbox.split(","))
    return DEFAULT_BBOX


def fetch_overture_places(bbox):
    """Pull real POIs from Overture Maps S3 via DuckDB."""
    import duckdb

    lon_min, lat_min, lon_max, lat_max = bbox
    log.info("Connecting to Overture Maps S3 (bbox: %.4f,%.4f -> %.4f,%.4f)",
             lon_min, lat_min, lon_max, lat_max)

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
    FROM read_parquet(
        's3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*'
    )
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


def upsert_places(conn, rows):
    """Upsert Overture places into Postgres, adding lat/lon columns."""
    cur = conn.cursor()

    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'places' AND column_name = 'lat'")
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


def extract_primary_category(cats_raw) -> str:
    """Extract the primary category string from Overture's categories field."""
    if not cats_raw:
        return "uncategorized"
    if isinstance(cats_raw, str):
        try:
            cats_raw = json.loads(cats_raw)
        except (json.JSONDecodeError, TypeError):
            return "uncategorized"
    if isinstance(cats_raw, dict):
        return str(cats_raw.get("primary", cats_raw.get("main", "uncategorized")))
    if isinstance(cats_raw, list) and cats_raw:
        return str(cats_raw[0])
    return "uncategorized"


def pick_visit_hour(category: str) -> int:
    """Sample a realistic visit hour based on POI category."""
    profile_key = CATEGORY_TO_PROFILE.get(category, "default")
    profile = VISIT_PROFILES[profile_key]
    hours = list(profile.keys())
    weights = list(profile.values())
    return random.choices(hours, weights=weights, k=1)[0]


def gps_jitter(lat: float, lon: float, max_meters: float = 25.0):
    """Add realistic GPS noise (uniform within max_meters radius)."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(3, max_meters)
    dlat = (distance / 111_000) * math.cos(angle)
    dlon = (distance / (111_000 * math.cos(math.radians(lat)))) * math.sin(angle)
    return round(lat + dlat, 7), round(lon + dlon, 7)


def generate_gps_points(conn, count: int):
    """Generate GPS visit points from real POI locations in the database."""
    import h3
    from app.config import settings

    cur = conn.cursor()

    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'places' AND column_name = 'lat'")
    has_latlon = cur.fetchone() is not None

    if has_latlon:
        cur.execute("SELECT id, lat, lon, categories::text FROM places WHERE lat IS NOT NULL")
    else:
        cur.execute("""
            SELECT id,
                   ST_Y(ST_Centroid(geometry::geometry)) AS lat,
                   ST_X(ST_Centroid(geometry::geometry)) AS lon,
                   categories::text
            FROM places
        """)

    all_pois = cur.fetchall()
    if not all_pois:
        log.error("No places in database. Load Overture data first.")
        cur.close()
        return 0

    log.info("Sampling %d GPS points from %d real POIs", count, len(all_pois))

    base_date = datetime.date(2026, 3, 1)
    created = 0

    for i in range(count):
        poi_id, poi_lat, poi_lon, cats_text = random.choice(all_pois)
        category = extract_primary_category(cats_text)

        lat, lon = gps_jitter(poi_lat, poi_lon, max_meters=20.0)

        day_offset = random.randint(0, 27)
        visit_date = base_date + datetime.timedelta(days=day_offset)
        hour = pick_visit_hour(category)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        ts = datetime.datetime(
            visit_date.year, visit_date.month, visit_date.day,
            hour, minute, second,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-8)),
        )

        h3_cell = h3.latlng_to_cell(lat, lon, settings.h3_resolution)
        gps_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO gps_points (id, lat, lon, timestamp, source, h3_cell, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (gps_id, lat, lon, ts, f"overture:{poi_id}", h3_cell))
        created += 1

    conn.commit()
    cur.close()
    log.info("Inserted %d GPS visit points with timestamps and H3 cells", created)
    return created


def cleanup_old_data(conn):
    """Remove hand-crafted seed rows (poi-1..poi-N style IDs, null timestamps)."""
    cur = conn.cursor()

    cur.execute("DELETE FROM answers WHERE question_id IN "
                "(SELECT id FROM questions WHERE gps_point_id IN "
                "(SELECT id FROM gps_points WHERE source IS NULL AND timestamp IS NULL))")
    cur.execute("DELETE FROM questions WHERE gps_point_id IN "
                "(SELECT id FROM gps_points WHERE source IS NULL AND timestamp IS NULL)")
    cur.execute("DELETE FROM gps_points WHERE source IS NULL AND timestamp IS NULL")
    deleted = cur.rowcount
    log.info("Cleaned up %d old GPS points (no source, no timestamp)", deleted)

    cur.execute("DELETE FROM places WHERE id LIKE 'poi-%%'")
    deleted_places = cur.rowcount
    log.info("Cleaned up %d old hand-crafted places", deleted_places)

    conn.commit()
    cur.close()


def main():
    args = parse_args()
    bbox = get_bbox(args)

    from app.config import settings
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    import psycopg2
    conn = psycopg2.connect(db_url)
    log.info("Connected to database")

    # Step 1: Fetch real Overture data
    overture_rows = fetch_overture_places(bbox)
    if not overture_rows:
        log.error("No places returned from Overture. Check bbox and network.")
        conn.close()
        sys.exit(1)

    # Step 2: Upsert into places table
    upsert_places(conn, overture_rows)

    # Step 3: Clean up old toy data
    if not args.keep_old:
        cleanup_old_data(conn)

    # Step 4: Generate GPS visit points
    generate_gps_points(conn, count=args.gps_count)

    # Summary
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM places")
    places_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gps_points")
    gps_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gps_points WHERE timestamp IS NOT NULL")
    ts_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gps_points WHERE h3_cell IS NOT NULL")
    h3_count = cur.fetchone()[0]
    cur.close()

    log.info("=== Database Summary ===")
    log.info("  Places:                 %d", places_count)
    log.info("  GPS points:             %d", gps_count)
    log.info("  GPS with timestamps:    %d", ts_count)
    log.info("  GPS with H3 cells:      %d", h3_count)

    conn.close()
    log.info("Done.")


if __name__ == "__main__":
    main()
