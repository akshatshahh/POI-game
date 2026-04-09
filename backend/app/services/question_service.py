"""Service for selecting and creating game questions."""

import uuid

import h3
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Answer, GpsPoint, Question
from app.regions import point_in_los_angeles
from app.services.poi_service import get_nearby_pois


def _lat_lon_to_h3(lat: float, lon: float) -> str:
    return h3.latlng_to_cell(lat, lon, settings.h3_resolution)


async def fetch_user_used_poi_ids(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Overture place IDs this user has already selected in a prior answer."""
    result = await db.execute(
        select(Answer.selected_poi_id).where(Answer.user_id == user_id)
    )
    return {str(x) for x in result.scalars().all()}


def _gps_in_study_area(lat: float, lon: float) -> bool:
    if not settings.restrict_gps_to_la:
        return True
    return point_in_los_angeles(lat, lon)


async def build_candidates_excluding_used_pois(
    db: AsyncSession,
    lat: float,
    lon: float,
    excluded: set[str],
    min_needed: int,
) -> list[dict]:
    """Nearby POIs, excluding place IDs the user already picked on a past question.

    Oversamples from the DB when many nearby POIs are filtered out.
    """
    max_out = settings.poi_max_candidates
    for mult in (3, 6, 12, 24, 48):
        cap = max(max_out * mult, min_needed * mult)
        pois = await get_nearby_pois(db, lat=lat, lon=lon, max_results=min(cap, 400))
        filtered = [p for p in pois if p["id"] not in excluded]
        if len(filtered) >= min_needed:
            return filtered[:max_out]
    return []


async def get_next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int = 3,
) -> dict | None:
    """Select the next unanswered question for a user.

    Strategy (v2):
    When use_h3_dedup is enabled, exclude GPS points whose H3 cell has
    already been answered by this user. Falls back to exact GPS-point
    exclusion when the flag is off or H3 cells are not yet populated.
    """
    if settings.use_h3_dedup:
        return await _next_question_h3(db, user_id, min_candidates)
    return await _next_question_legacy(db, user_id, min_candidates)


async def _next_question_legacy(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int,
) -> dict | None:
    """Original per-GPS-point exclusion strategy."""
    answered_subq = (
        select(Question.gps_point_id)
        .join(Answer, Answer.question_id == Question.id)
        .where(Answer.user_id == user_id)
        .correlate()
        .scalar_subquery()
    )

    answer_count = (
        select(func.count(Answer.id))
        .join(Question, Question.id == Answer.question_id)
        .where(Question.gps_point_id == GpsPoint.id)
        .correlate(GpsPoint)
        .scalar_subquery()
    )

    stmt = (
        select(GpsPoint)
        .where(GpsPoint.id.notin_(answered_subq))
        .order_by(answer_count.asc(), func.random())
        .limit(5)
    )

    result = await db.execute(stmt)
    gps_rows = result.scalars().all()
    excluded_pois = await fetch_user_used_poi_ids(db, user_id)

    for gps_point in gps_rows:
        if not _gps_in_study_area(gps_point.lat, gps_point.lon):
            continue
        pois = await build_candidates_excluding_used_pois(
            db, gps_point.lat, gps_point.lon, excluded_pois, min_candidates
        )
        if len(pois) < min_candidates:
            continue

        question = await _get_or_create_question(db, gps_point)
        return _build_response(question, gps_point, pois)

    return None


async def _next_question_h3(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int,
) -> dict | None:
    """H3-based exclusion: skip GPS points in cells already answered."""
    answered_cells_subq = (
        select(Question.h3_cell)
        .join(Answer, Answer.question_id == Question.id)
        .where(Answer.user_id == user_id)
        .where(Question.h3_cell.isnot(None))
        .correlate()
        .scalar_subquery()
    )

    answer_count = (
        select(func.count(Answer.id))
        .join(Question, Question.id == Answer.question_id)
        .where(Question.gps_point_id == GpsPoint.id)
        .correlate(GpsPoint)
        .scalar_subquery()
    )

    stmt = (
        select(GpsPoint)
        .where(GpsPoint.h3_cell.isnot(None))
        .where(GpsPoint.h3_cell.notin_(answered_cells_subq))
        .order_by(answer_count.asc(), func.random())
        .limit(5)
    )

    result = await db.execute(stmt)
    gps_rows = result.scalars().all()
    excluded_pois = await fetch_user_used_poi_ids(db, user_id)

    for gps_point in gps_rows:
        if not _gps_in_study_area(gps_point.lat, gps_point.lon):
            continue
        pois = await build_candidates_excluding_used_pois(
            db, gps_point.lat, gps_point.lon, excluded_pois, min_candidates
        )
        if len(pois) < min_candidates:
            continue

        question = await _get_or_create_question(db, gps_point)
        return _build_response(question, gps_point, pois)

    return None


def _build_response(question: Question, gps_point: GpsPoint, pois: list[dict]) -> dict:
    ts = gps_point.timestamp
    return {
        "question_id": str(question.id),
        "gps_point": {
            "lat": gps_point.lat,
            "lon": gps_point.lon,
            "timestamp": ts.isoformat() if ts else None,
            "weekday": ts.strftime("%A") if ts else None,
            "local_date": ts.strftime("%B %d, %Y") if ts else None,
            "local_time": ts.strftime("%I:%M %p") if ts else None,
        },
        "candidates": pois,
    }


async def _get_or_create_question(
    db: AsyncSession,
    gps_point: GpsPoint,
) -> Question:
    result = await db.execute(
        select(Question).where(
            Question.gps_point_id == gps_point.id,
            Question.status == "active",
        )
    )
    question = result.scalar_one_or_none()

    if question is None:
        h3_cell = gps_point.h3_cell or _lat_lon_to_h3(gps_point.lat, gps_point.lon)
        question = Question(
            gps_point_id=gps_point.id,
            h3_cell=h3_cell,
            status="active",
        )
        db.add(question)
        await db.flush()

    return question
