"""Service for selecting and creating game questions."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, GpsPoint, Question
from app.services.poi_service import get_nearby_pois


async def get_next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int = 3,
) -> dict | None:
    """Select the next unanswered question for a user.

    Strategy (v1):
    1. Find GPS points that this user has NOT yet answered.
    2. Prefer GPS points with fewer total answers (need more labels).
    3. Create a Question record if one doesn't exist for the chosen GPS point.
    4. Fetch nearby POIs as candidate answers.
    5. Skip GPS points that have fewer than min_candidates nearby POIs.
    """
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

        question = await _get_or_create_question(db, gps_point.id)

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

    return None


async def _get_or_create_question(
    db: AsyncSession,
    gps_point_id: uuid.UUID,
) -> Question:
    result = await db.execute(
        select(Question).where(
            Question.gps_point_id == gps_point_id,
            Question.status == "active",
        )
    )
    question = result.scalar_one_or_none()

    if question is None:
        question = Question(gps_point_id=gps_point_id, status="active")
        db.add(question)
        await db.flush()

    return question
