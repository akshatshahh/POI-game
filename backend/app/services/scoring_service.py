"""Scoring logic for answer evaluation.

v1 approach: consensus-based scoring.
After each answer, compute the most-chosen POI for that question.
If user's answer matches the consensus, award full points.
Otherwise award participation points.

Designed as a standalone module for easy future refinement
(e.g., weighted consensus, distance-based scoring, expert labels).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer

FULL_POINTS = 10
PARTICIPATION_POINTS = 2
MIN_ANSWERS_FOR_CONSENSUS = 2


async def compute_score(
    db: AsyncSession,
    question_id: uuid.UUID,
    selected_poi_id: str,
) -> int:
    """Compute the score for a given answer based on current consensus.

    Returns FULL_POINTS if the selected POI matches the most popular choice,
    PARTICIPATION_POINTS otherwise. If there aren't enough answers yet for
    consensus, awards PARTICIPATION_POINTS as a baseline.
    """
    result = await db.execute(
        select(Answer.selected_poi_id, func.count(Answer.id).label("cnt"))
        .where(Answer.question_id == question_id)
        .group_by(Answer.selected_poi_id)
        .order_by(func.count(Answer.id).desc())
        .limit(1)
    )
    row = result.first()

    if row is None or row.cnt < MIN_ANSWERS_FOR_CONSENSUS:
        return PARTICIPATION_POINTS

    consensus_poi_id = row.selected_poi_id
    if selected_poi_id == consensus_poi_id:
        return FULL_POINTS

    return PARTICIPATION_POINTS


async def retroactive_score_update(
    db: AsyncSession,
    question_id: uuid.UUID,
) -> None:
    """Re-evaluate scores for all answers on a question after a new answer.

    When consensus shifts, update score_awarded for each answer and
    adjust user totals accordingly. This keeps scores accurate as
    more labels come in.
    """
    result = await db.execute(
        select(Answer.selected_poi_id, func.count(Answer.id).label("cnt"))
        .where(Answer.question_id == question_id)
        .group_by(Answer.selected_poi_id)
        .order_by(func.count(Answer.id).desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        return

    consensus_poi_id = row.selected_poi_id
    total_answers = row.cnt

    if total_answers < MIN_ANSWERS_FOR_CONSENSUS:
        return

    answers_result = await db.execute(
        select(Answer).where(Answer.question_id == question_id)
    )
    answers = answers_result.scalars().all()

    for answer in answers:
        new_score = FULL_POINTS if answer.selected_poi_id == consensus_poi_id else PARTICIPATION_POINTS
        if answer.score_awarded != new_score:
            from app.models import User
            score_diff = new_score - answer.score_awarded
            answer.score_awarded = new_score

            user_result = await db.execute(select(User).where(User.id == answer.user_id))
            user = user_result.scalar_one()
            user.score += score_diff

    await db.flush()
