"""Endpoints for querying nearby POIs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import PoiResponse
from app.services.poi_service import get_nearby_pois

router = APIRouter(prefix="/pois", tags=["pois"])


@router.get("/nearby", response_model=list[PoiResponse])
async def nearby_pois(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius: int = Query(200, ge=10, le=5000, description="Search radius in meters"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await get_nearby_pois(db, lat=lat, lon=lon, radius_meters=radius, max_results=limit)
