"""Service for selecting and creating game questions."""

import uuid

import h3
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Answer, GpsPoint, Question
from app.services.poi_service import get_nearby_pois


def _lat_lon_to_h3(lat: float, lon: float) -> str:
    return h3.latlng_to_cell(lat, lon, settings.h3_resolution)


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
    candidates = result.scalars().all()

    for gps_point in candidates:
        pois = await get_nearby_pois(db, lat=gps_point.lat, lon=gps_point.lon)
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
    candidates = result.scalars().all()

    for gps_point in candidates:
        pois = await get_nearby_pois(db, lat=gps_point.lat, lon=gps_point.lon)
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
