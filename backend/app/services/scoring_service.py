"""Scoring logic for answer evaluation.

Combination approach:
  Base points (5)     — awarded for every answer (rewards participation)
  Distance bonus (1-5) — closer selected POI to GPS point = more bonus (rewards skill)
  Consensus bonus (10) — awarded retroactively when 2+ players pick the same POI

Single player sees 6-10 points immediately.
When others agree, scores bump up to 16-20.

Each component is stored on the Answer row; score_awarded is their sum.
"""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, User

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


def apply_initial_score(answer: Answer, distance_meters: float) -> int:
    """Set the immediate score components on a new answer.

    Consensus bonus starts at 0 and is granted later by
    retroactive_score_update. Returns the awarded total.
    """
    answer.base_points = BASE_POINTS
    answer.distance_bonus = distance_bonus(distance_meters)
    answer.consensus_bonus = 0
    answer.score_awarded = answer.base_points + answer.distance_bonus
    return answer.score_awarded


async def retroactive_score_update(
    db: AsyncSession,
    question_id: uuid.UUID,
) -> None:
    """Re-evaluate consensus bonus for all answers on a question.

    When 2+ players pick the same POI, all of them get the consensus bonus.
    If consensus shifts, bonuses are adjusted accordingly (scores can go down).
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
    consensus_count = row.cnt

    answers_result = await db.execute(
        select(Answer).where(Answer.question_id == question_id)
    )
    answers = answers_result.scalars().all()

    score_diffs: dict[uuid.UUID, int] = defaultdict(int)
    for answer in answers:
        earned_consensus = (
            consensus_count >= MIN_ANSWERS_FOR_CONSENSUS
            and answer.selected_poi_id == consensus_poi_id
        )
        new_bonus = CONSENSUS_BONUS if earned_consensus else 0
        if answer.consensus_bonus != new_bonus:
            score_diffs[answer.user_id] += new_bonus - answer.consensus_bonus
            answer.consensus_bonus = new_bonus
            answer.score_awarded = (
                answer.base_points + answer.distance_bonus + answer.consensus_bonus
            )

    if score_diffs:
        users_result = await db.execute(
            select(User).where(User.id.in_(score_diffs.keys()))
        )
        for user in users_result.scalars():
            user.score += score_diffs[user.id]

    await db.flush()
