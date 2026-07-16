"""Scoring and consensus logic.

Scoring:
  Base points (5)      — for every answer, immediately (rewards participation)
  Consensus bonus (10) — paid ONCE, when the question locks, to everyone who
                         picked the winning POI
  Difficulty bonus (5) — added to the consensus bonus on questions that
                         needed the escalated annotation target

Nothing is paid before lock, so scores never go down.

Consensus (per question):
  1. Collect at least MIN_VOTES_FOR_CONSENSUS independent answers.
  2. The leading POI wins when it has >= MAJORITY_FRACTION of votes AND a
     lead of >= MIN_VOTE_LEAD over the runner-up. A 2-2 tie can never pass,
     so ties resolve themselves by collecting more votes.
  3. If the base target is reached without consensus (or the area is dense),
     the target escalates to settings.consensus_max_target.
  4. At the escalated target the decision is final either way:
     status becomes consensus_reached or no_consensus and the question locks.
  Locked labels are immutable; exports are reproducible.
"""

import datetime
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Answer, Question, User

BASE_POINTS = 5
CONSENSUS_BONUS = 10
DIFFICULTY_BONUS = 5

MIN_VOTES_FOR_CONSENSUS = 3
MAJORITY_FRACTION = 0.6
MIN_VOTE_LEAD = 2

STATUS_ACTIVE = "active"
STATUS_CONSENSUS = "consensus_reached"
STATUS_NO_CONSENSUS = "no_consensus"
TERMINAL_STATUSES = (STATUS_CONSENSUS, STATUS_NO_CONSENSUS)


def apply_initial_score(answer: Answer, distance_meters: float | None) -> int:
    """Set the immediate (participation-only) score on a new answer.

    The distance is recorded as an ML covariate but deliberately does not
    affect the score: rewarding proximity would train annotators to pick
    the nearest pin instead of the true visit. Returns the awarded total.
    """
    answer.selected_distance_meters = distance_meters
    answer.base_points = BASE_POINTS
    answer.distance_bonus = 0
    answer.consensus_bonus = 0
    answer.score_awarded = BASE_POINTS
    return answer.score_awarded


async def _eligible_vote_counts(
    db: AsyncSession, question_id: uuid.UUID
) -> list[tuple[str, int]]:
    """Vote counts per POI, descending, counting only Sybil-gated users."""
    stmt = (
        select(Answer.selected_poi_id, func.count(Answer.id).label("cnt"))
        .where(Answer.question_id == question_id)
        .group_by(Answer.selected_poi_id)
        .order_by(func.count(Answer.id).desc())
    )
    if settings.consensus_min_account_age_minutes > 0:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            minutes=settings.consensus_min_account_age_minutes
        )
        stmt = (
            select(Answer.selected_poi_id, func.count(Answer.id).label("cnt"))
            .join(User, User.id == Answer.user_id)
            .where(Answer.question_id == question_id, User.created_at <= cutoff)
            .group_by(Answer.selected_poi_id)
            .order_by(func.count(Answer.id).desc())
        )
    result = await db.execute(stmt)
    return [(row.selected_poi_id, row.cnt) for row in result.all()]


def _has_consensus(counts: list[tuple[str, int]]) -> tuple[str, float] | None:
    """Return (winning_poi_id, confidence) if the consensus condition holds."""
    total = sum(cnt for _, cnt in counts)
    if total < MIN_VOTES_FOR_CONSENSUS:
        return None
    top_votes = counts[0][1]
    second_votes = counts[1][1] if len(counts) > 1 else 0
    if top_votes / total >= MAJORITY_FRACTION and top_votes - second_votes >= MIN_VOTE_LEAD:
        return counts[0][0], top_votes / total
    return None


async def _pay_consensus_bonus(db: AsyncSession, question: Question) -> None:
    """Pay the lock-time bonus to every answer matching the winning POI."""
    bonus = CONSENSUS_BONUS
    if question.answers_target > settings.consensus_base_target:
        bonus += DIFFICULTY_BONUS

    result = await db.execute(
        select(Answer).where(
            Answer.question_id == question.id,
            Answer.selected_poi_id == question.consensus_poi_id,
        )
    )
    matching = result.scalars().all()

    score_diffs: dict[uuid.UUID, int] = defaultdict(int)
    for answer in matching:
        answer.consensus_bonus = bonus
        answer.score_awarded = answer.base_points + bonus
        score_diffs[answer.user_id] += bonus

    if score_diffs:
        users_result = await db.execute(select(User).where(User.id.in_(score_diffs.keys())))
        for user in users_result.scalars():
            user.score += score_diffs[user.id]


async def evaluate_consensus(db: AsyncSession, question: Question) -> None:
    """Re-evaluate a question's consensus state after a new answer.

    Escalates the annotation target on disagreement, and locks the question
    (terminal status + payout) once the evidence is decisive or exhausted.
    """
    if question.locked_at is not None:
        return

    counts = await _eligible_vote_counts(db, question.id)
    total_votes = sum(cnt for _, cnt in counts)
    question.votes_total = total_votes

    consensus = _has_consensus(counts)
    if consensus is not None:
        poi_id, confidence = consensus
        question.status = STATUS_CONSENSUS
        question.consensus_poi_id = poi_id
        question.consensus_confidence = round(confidence, 4)
        question.locked_at = datetime.datetime.now(datetime.timezone.utc)
        await _pay_consensus_bonus(db, question)
        await db.flush()
        return

    if total_votes >= question.answers_target:
        if question.answers_target < settings.consensus_max_target:
            # Annotators disagree at the base target: collect more evidence
            # before finalizing.
            question.answers_target = settings.consensus_max_target
        else:
            # Evidence exhausted without agreement — a documented ambiguous
            # point. No bonus is paid; the label exports as no_consensus.
            question.status = STATUS_NO_CONSENSUS
            question.consensus_confidence = (
                round(counts[0][1] / total_votes, 4) if counts else None
            )
            question.locked_at = datetime.datetime.now(datetime.timezone.utc)

    await db.flush()
