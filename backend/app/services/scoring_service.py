"""Scoring and agreement tracking.

Scoring:
  Base points (5) — for every answer, immediately (rewards participation)

Distance is recorded as an ML covariate but never scored. Nothing is paid
at lock: average pairwise Jaccard measures agreement between sets, and it
does not name a winning place, so there is no consensus bonus.

Agreement and sampling (per question):
  1. Each eligible answer is a set of POI ids (selected_poi_ids, with a
     fallback to the stored primary id).
  2. Pairwise Jaccard is |A∩B| / |A∪B|. The question score is the mean
     over all n(n−1)/2 unordered pairs (undefined when n < 2).
  3. Every question collects at least CONSENSUS_MIN_ANSWERS (5) eligible
     responses. While any open question is below that floor, those are
     served first.
  4. After every open question has at least 5, more responses go to the
     lowest average Jaccard among questions with 5–9.
  5. At CONSENSUS_MAX_ANSWERS (10) the question is complete regardless of
     Jaccard. It locks as no_consensus with no named place and is not
     presented again. Locked rows are immutable.
"""

import datetime
import uuid
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Answer, Question, User

BASE_POINTS = 5

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


def answer_selection_set(answer: Answer) -> set[str] | None:
    """POI ids this answer counts as, or None if the row has no usable set."""
    raw_ids = answer.selected_poi_ids
    if raw_ids:
        values = {str(item) for item in raw_ids if item}
        if values:
            return values
    if answer.selected_poi_id:
        return {str(answer.selected_poi_id)}
    return None


def mean_pairwise_jaccard(sets: list[set[str]]) -> float | None:
    """Mean Jaccard similarity over all unordered pairs.

    Returns None when there are fewer than two sets, or when every pair
    has an empty union (empty sets are a data error; the API rejects them).
    Identical non-empty sets score 1.0; disjoint sets score 0.0.
    """
    if len(sets) < 2:
        return None
    total = 0.0
    pairs = 0
    for left, right in combinations(sets, 2):
        union = left | right
        if not union:
            continue
        total += len(left & right) / len(union)
        pairs += 1
    if pairs == 0:
        return None
    return total / pairs


def _sybil_cutoff() -> datetime.datetime | None:
    minutes = settings.consensus_min_account_age_minutes
    if minutes <= 0:
        return None
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=minutes
    )


async def eligible_selection_sets_by_question(
    db: AsyncSession, question_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[set[str]]]:
    """Sybil-gated selection sets for each question, keyed by question id."""
    grouped: dict[uuid.UUID, list[set[str]]] = {qid: [] for qid in question_ids}
    if not question_ids:
        return grouped

    stmt = select(Answer).where(Answer.question_id.in_(question_ids))
    cutoff = _sybil_cutoff()
    if cutoff is not None:
        stmt = (
            select(Answer)
            .join(User, User.id == Answer.user_id)
            .where(Answer.question_id.in_(question_ids), User.created_at <= cutoff)
        )
    result = await db.execute(stmt)
    for answer in result.scalars():
        selection = answer_selection_set(answer)
        if selection:
            grouped[answer.question_id].append(selection)
    return grouped


async def eligible_selection_sets(
    db: AsyncSession, question_id: uuid.UUID
) -> list[set[str]]:
    grouped = await eligible_selection_sets_by_question(db, [question_id])
    return grouped.get(question_id, [])


async def evaluate_consensus(db: AsyncSession, question: Question) -> None:
    """Update agreement stats after a new answer and lock at the cap.

    Jaccard does not elect a place, so a completed question is stored as
    no_consensus with a null consensus_poi_id. consensus_confidence is the
    mean pairwise Jaccard (None until there are two eligible sets).
    """
    if question.locked_at is not None:
        return

    sets = await eligible_selection_sets(db, question.id)
    n = len(sets)
    question.votes_total = n
    question.answers_target = settings.consensus_max_answers
    jaccard = mean_pairwise_jaccard(sets)
    question.consensus_confidence = None if jaccard is None else round(jaccard, 4)

    if n >= question.answers_target:
        question.status = STATUS_NO_CONSENSUS
        question.consensus_poi_id = None
        question.locked_at = datetime.datetime.now(datetime.timezone.utc)

    await db.flush()
