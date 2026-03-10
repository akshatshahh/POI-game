"""Scoring logic for answer evaluation.

Combination approach:
  Base points (5)     — awarded for every answer (rewards participation)
  Distance bonus (1-5) — closer selected POI to GPS point = more bonus (rewards skill)
  Consensus bonus (10) — awarded retroactively when 2+ players pick the same POI

Single player sees 6-10 points immediately.
When others agree, scores bump up to 16-20.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer

BASE_POINTS = 5
MAX_DISTANCE_BONUS = 5
CONSENSUS_BONUS = 10
MIN_ANSWERS_FOR_CONSENSUS = 2


def distance_bonus(distance_meters: float) -> int:
    """Award 1-5 bonus points based on proximity.

    <= 50m  → 5 pts
    <= 100m → 4 pts
    <= 200m → 3 pts
    <= 350m → 2 pts
    > 350m  → 1 pt
    """
    if distance_meters <= 50:
        return 5
    if distance_meters <= 100:
        return 4
    if distance_meters <= 200:
        return 3
    if distance_meters <= 350:
        return 2
    return 1


async def compute_score(
    db: AsyncSession,
    question_id: uuid.UUID,
    selected_poi_id: str,
    selected_poi_distance: float = 0.0,
) -> int:
    """Compute immediate score: base + distance bonus.

    Consensus bonus is handled separately via retroactive_score_update.
    """
    return BASE_POINTS + distance_bonus(selected_poi_distance)


async def retroactive_score_update(
    db: AsyncSession,
    question_id: uuid.UUID,
) -> None:
    """Re-evaluate consensus bonus for all answers on a question.

    When 2+ players pick the same POI, all of them get the consensus bonus.
    If consensus shifts, bonuses are adjusted accordingly.
    """
    from app.models import User

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
    consensus_count = row.cnt

    answers_result = await db.execute(
        select(Answer).where(Answer.question_id == question_id)
    )
    answers = answers_result.scalars().all()

    for answer in answers:
        base_and_dist = BASE_POINTS + distance_bonus(0)
        if answer.score_awarded > BASE_POINTS + MAX_DISTANCE_BONUS:
            base_and_dist = answer.score_awarded - CONSENSUS_BONUS
        elif answer.score_awarded >= BASE_POINTS:
            base_and_dist = answer.score_awarded

        earned_consensus = (
            consensus_count >= MIN_ANSWERS_FOR_CONSENSUS
            and answer.selected_poi_id == consensus_poi_id
        )
        new_score = base_and_dist + (CONSENSUS_BONUS if earned_consensus else 0)

        if answer.score_awarded != new_score:
            score_diff = new_score - answer.score_awarded
            answer.score_awarded = new_score

            user_result = await db.execute(select(User).where(User.id == answer.user_id))
            user = user_result.scalar_one()
            user.score += score_diff

    await db.flush()
