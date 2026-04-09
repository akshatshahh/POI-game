#!/usr/bin/env python3
"""Load Overture Maps places into the local `places` table.

Usage:
    python scripts/load_overture_places.py           # default USC bounding box
    python scripts/load_overture_places.py --bbox "-118.30,34.01,-118.27,34.03"

Requires: duckdb, asyncpg (or psycopg2), sqlalchemy
Reads DATABASE_URL from the backend .env (via app.config).

The script:
  1. Queries the Overture Maps S3 parquet directly via DuckDB.
  2. Filters by bounding box and an expanded category list.
  3. Upserts rows into the local Postgres `places` table.
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Broad Overture category set for a dense, realistic campus-area POI map
EXPANDED_CATEGORIES = [
    "restaurant",
    "fast_food",
    "cafe",
    "bar",
    "pub",
    "coffee_shop",
    "bakery",
    "ice_cream",
    "food_court",
    "convenience_store",
    "grocery",
    "supermarket",
    "pharmacy",
    "bank",
    "atm",
    "post_office",
    "library",
    "university",
    "school",
    "college",
    "kindergarten",
    "hospital",
    "clinic",
    "dentist",
    "doctor",
    "veterinary",
    "gym",
    "fitness_center",
    "sports_centre",
    "swimming_pool",
    "park",
    "playground",
    "garden",
    "museum",
    "art_gallery",
    "theatre",
    "cinema",
    "nightclub",
    "place_of_worship",
    "church",
    "mosque",
    "temple",
    "bus_station",
    "train_station",
    "subway_station",
    "parking",
    "fuel",
    "gas_station",
    "car_wash",
    "car_repair",
    "hotel",
    "hostel",
    "motel",
    "beauty_salon",
    "hair_salon",
    "barbershop",
    "laundry",
    "dry_cleaning",
    "clothing_store",
    "shoe_store",
    "bookstore",
    "electronics_store",
    "department_store",
    "shopping_mall",
    "hardware_store",
    "pet_store",
    "florist",
    "optician",
    "tattoo",
    "office",
    "coworking_space",
    "community_center",
    "fire_station",
    "police",
    "embassy",
    "townhall",
]

USC_BBOX = (-118.295, 34.015, -118.275, 34.030)


def parse_args():
    p = argparse.ArgumentParser(description="Load Overture places into Postgres")
    p.add_argument(
        "--bbox",
        type=str,
        default=None,
        help="lon_min,lat_min,lon_max,lat_max  (default: USC campus area)",
    )
    p.add_argument(
        "--radius-km",
        type=float,
        default=None,
        help="Alternative: radius in km around USC center (34.0224, -118.2851)",
    )
    return p.parse_args()


def build_bbox(args):
    if args.bbox:
        parts = [float(x) for x in args.bbox.split(",")]
        return tuple(parts)
    if args.radius_km:
        km = args.radius_km
        deg_lat = km / 111.0
        deg_lon = km / (111.0 * 0.82)  # cos(34°) ≈ 0.82
        return (
            -118.2851 - deg_lon,
            34.0224 - deg_lat,
            -118.2851 + deg_lon,
            34.0224 + deg_lat,
        )
    return USC_BBOX


def main():
    args = parse_args()
    bbox = build_bbox(args)
    lon_min, lat_min, lon_max, lat_max = bbox

    try:
        import duckdb
    except ImportError:
        print("ERROR: duckdb is required. Install with: pip install duckdb")
        sys.exit(1)

    print(f"Bounding box: lon[{lon_min},{lon_max}] lat[{lat_min},{lat_max}]")
    print(f"Categories: {len(EXPANDED_CATEGORIES)} types")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-west-2';")

    cat_list = ", ".join(f"'{c}'" for c in EXPANDED_CATEGORIES)

    query = f"""
    SELECT
        id,
        names,
        categories,
        ST_Y(ST_Centroid(geometry)) AS lat,
        ST_X(ST_Centroid(geometry)) AS lon,
        ST_AsText(geometry) AS wkt
    FROM read_parquet('s3://overturemaps-us-west-2/release/2024-07-22.0/theme=places/type=place/*')
    WHERE bbox.xmin >= {lon_min}
      AND bbox.xmax <= {lon_max}
      AND bbox.ymin >= {lat_min}
      AND bbox.ymax <= {lat_max}
    """

    print("Querying Overture Maps S3 (may take 1-2 minutes)...")
    rows = con.execute(query).fetchall()
    columns = ["id", "names", "categories", "lat", "lon", "wkt"]
    print(f"Fetched {len(rows)} raw places from Overture")

    from app.config import settings
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 required. Install with: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
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
    conn.close()

    print(f"Upserted {inserted} places into Postgres")
    print("Done.")


if __name__ == "__main__":
    main()
