#!/usr/bin/env python3
"""Backfill h3_cell for existing gps_points rows that are missing it.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/backfill_h3.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import h3
from sqlalchemy import select, update

from app.config import settings
from app.database import async_session_factory
from app.models import GpsPoint


async def backfill():
    async with async_session_factory() as db:
        result = await db.execute(
            select(GpsPoint).where(GpsPoint.h3_cell.is_(None))
        )
        points = result.scalars().all()

        if not points:
            print("All GPS points already have h3_cell values.")
            return

        count = 0
        for gp in points:
            cell = h3.latlng_to_cell(gp.lat, gp.lon, settings.h3_resolution)
            await db.execute(
                update(GpsPoint)
                .where(GpsPoint.id == gp.id)
                .values(h3_cell=cell)
            )
            count += 1

        await db.commit()
        print(f"Backfilled {count} GPS points with H3 cells (resolution {settings.h3_resolution}).")


if __name__ == "__main__":
    asyncio.run(backfill())
