#!/usr/bin/env python3
"""Load Overture Maps places into the local `places` table (places only).

For a full seed (places + generated GPS visit points), use
seed_production_data.py instead — that is the canonical pipeline.
This script exists for reloading POIs on a local PostGIS database
without touching GPS points, questions, or answers.

Usage:
    python scripts/load_overture_places.py           # default Greater LA bounding box
    python scripts/load_overture_places.py --bbox "-118.67,33.70,-118.08,34.34"
    python scripts/load_overture_places.py --radius-km 3

Reads DATABASE_URL from the backend .env (via app.config).
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.regions import LOS_ANGELES_BBOX
from scripts.overture_common import (
    connect_postgres,
    ensure_places_table,
    fetch_overture_places,
    upsert_places,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

# USC campus center, used for the --radius-km convenience option.
USC_LAT, USC_LON = 34.0224, -118.2851


def parse_args():
    p = argparse.ArgumentParser(description="Load Overture places into Postgres")
    p.add_argument(
        "--bbox",
        type=str,
        default=None,
        help="lon_min,lat_min,lon_max,lat_max  (default: Greater Los Angeles)",
    )
    p.add_argument(
        "--radius-km",
        type=float,
        default=None,
        help=f"Alternative: radius in km around USC center ({USC_LAT}, {USC_LON})",
    )
    return p.parse_args()


def build_bbox(args):
    if args.bbox:
        return tuple(float(x) for x in args.bbox.split(","))
    if args.radius_km:
        km = args.radius_km
        deg_lat = km / 111.0
        deg_lon = km / (111.0 * 0.82)  # cos(34°) ≈ 0.82
        return (
            USC_LON - deg_lon,
            USC_LAT - deg_lat,
            USC_LON + deg_lon,
            USC_LAT + deg_lat,
        )
    return LOS_ANGELES_BBOX


def main():
    args = parse_args()
    bbox = build_bbox(args)

    rows = fetch_overture_places(bbox)
    if not rows:
        print("No places returned from Overture. Check bbox and network.")
        sys.exit(1)

    conn = connect_postgres()
    ensure_places_table(conn)
    inserted = upsert_places(conn, rows)
    conn.close()

    print(f"Upserted {inserted} places into Postgres")
    print("Done.")


if __name__ == "__main__":
    main()
