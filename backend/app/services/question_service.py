"""Service for selecting and creating game questions."""

import datetime
import random
import uuid
import zoneinfo

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.geo import lat_lon_to_h3
from app.models import Answer, GpsPoint, Question
from app.regions import point_in_los_angeles
from app.services.poi_service import get_nearby_pois
from app.services.scoring_service import (
    TERMINAL_STATUSES,
    eligible_selection_sets_by_question,
    mean_pairwise_jaccard,
)

# Question timestamps are shown in study-area local time (the game covers LA).
_LA_TZ = zoneinfo.ZoneInfo("America/Los_Angeles")

# A question needs at least this many candidate POIs to be playable.
# Answer validation in game_router uses the same threshold.
MIN_CANDIDATES = 3

# Hard cap on the candidate set frozen onto a question at creation.
_MAX_FROZEN_CANDIDATES = 400


def displayed_candidates(
    frozen: list[dict] | None,
    excluded_poi_ids: set[str],
    max_candidates: int | None = None,
) -> list[dict]:
    """The ordered subset a player is shown: frozen order, minus exclusions, capped."""
    limit = settings.poi_max_candidates if max_candidates is None else max_candidates
    return [
        candidate
        for candidate in (frozen or [])
        if candidate.get("id") not in excluded_poi_ids
    ][:limit]


def _to_la_time(ts: datetime.datetime) -> datetime.datetime:
    """Convert a naive UTC datetime (as stored in DB) to LA local time."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    return ts.astimezone(_LA_TZ)


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


async def get_next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int = MIN_CANDIDATES,
    exclude_question_id: uuid.UUID | None = None,
) -> dict | None:
    """Select the next unanswered question for a user.

    Strategy (v2):
    When use_h3_dedup is enabled, exclude GPS points whose H3 cell has
    already been answered by this user. Falls back to exact GPS-point
    exclusion when the flag is off or H3 cells are not yet populated.
    """
    # Points whose question already reached a terminal state (label locked)
    # are finished — never serve them again.
    closed_points = (
        select(Question.gps_point_id)
        .where(Question.status.in_(TERMINAL_STATUSES))
        .scalar_subquery()
    )
    exclusion: list[ColumnElement] = [GpsPoint.id.notin_(closed_points)]

    if exclude_question_id is not None:
        skipped_points = select(Question.gps_point_id).where(
            Question.id == exclude_question_id
        )
        exclusion.append(GpsPoint.id.notin_(skipped_points))

    if settings.use_h3_dedup:
        # Skip GPS points in H3 cells the user already answered.
        answered_cells = (
            select(Question.h3_cell)
            .join(Answer, Answer.question_id == Question.id)
            .where(Answer.user_id == user_id)
            .where(Question.h3_cell.isnot(None))
            .correlate()
            .scalar_subquery()
        )
        exclusion += [
            GpsPoint.h3_cell.isnot(None),
            GpsPoint.h3_cell.notin_(answered_cells),
        ]
    else:
        # Original strategy: skip only the exact GPS points already answered.
        answered_points = (
            select(Question.gps_point_id)
            .join(Answer, Answer.question_id == Question.id)
            .where(Answer.user_id == user_id)
            .correlate()
            .scalar_subquery()
        )
        exclusion.append(GpsPoint.id.notin_(answered_points))

    return await _next_question(db, user_id, min_candidates, exclusion)


def _selection_rank_key(n: int, jaccard: float | None) -> tuple:
    """Sort key: fill to min answers, then lowest Jaccard, then more answers.

    Band 0 is n < min; higher n first so unfinished visits are not starved
    by a stream of new GPS points. Band 1 is min <= n < max; lowest mean
    pairwise Jaccard first, then higher n. A trailing random value breaks
    remaining ties. Jaccard is ignored until a question has min answers.
    """
    tie = random.random()
    min_n = settings.consensus_min_answers
    if n < min_n:
        return (0, float(-n), 0.0, tie)
    similarity = 1.0 if jaccard is None else jaccard
    return (1, similarity, float(-n), tie)


async def _next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int,
    exclusion: list[ColumnElement],
) -> dict | None:
    """Pick the next eligible GPS point by the Jaccard sampling policy.

    1. Every question should receive at least the minimum eligible responses.
    2. While any open visit is below that floor, those are served first
       (highest n, then random).
    3. Once every open visit has at least the minimum, remaining questions
       are served from lowest average pairwise Jaccard to highest.
    4. A question is complete at the stored answers_target (10) regardless
       of Jaccard and is not presented again.
    5. Keep picking the lowest-Jaccard question among those with 5–9
       responses until every question is complete or otherwise excluded.
    """
    result = await db.execute(select(GpsPoint).where(*exclusion))
    gps_rows = [
        gps for gps in result.scalars().all() if _gps_in_study_area(gps.lat, gps.lon)
    ]
    if not gps_rows:
        return None

    gps_ids = [gps.id for gps in gps_rows]
    question_result = await db.execute(
        select(Question).where(
            Question.gps_point_id.in_(gps_ids),
            Question.status == "active",
        )
    )
    questions = question_result.scalars().all()
    question_by_gps = {question.gps_point_id: question for question in questions}
    sets_by_question = await eligible_selection_sets_by_question(
        db, [question.id for question in questions]
    )

    ranked: list[tuple[tuple, GpsPoint]] = []
    for gps_point in gps_rows:
        question = question_by_gps.get(gps_point.id)
        if question is None:
            n = 0
            jaccard = None
        else:
            sets = sets_by_question.get(question.id, [])
            n = len(sets)
            jaccard = mean_pairwise_jaccard(sets)
        cap = settings.consensus_max_answers
        if question is not None:
            cap = max(question.answers_target, settings.consensus_max_answers)
        if n >= cap:
            continue
        ranked.append((_selection_rank_key(n, jaccard), gps_point))

    ranked.sort(key=lambda item: item[0])
    excluded_pois = await fetch_user_used_poi_ids(db, user_id)

    for _, gps_point in ranked:
        question = await _get_or_create_question(db, gps_point)
        if question.candidate_density < min_candidates:
            continue

        # Shown options are a per-player slice of the frozen set. That slice
        # is stored on the answer at submit so exports can recover it.
        shown = displayed_candidates(question.candidates, excluded_pois)
        if len(shown) < min_candidates:
            continue

        prior = await db.execute(
            select(func.count(Answer.id)).where(Answer.question_id == question.id)
        )
        return _build_response(question, gps_point, shown, int(prior.scalar() or 0))

    return None


def _format_visit_time(local_ts: datetime.datetime) -> str:
    """Compact local time for the UI, e.g. '4:42pm'."""
    return local_ts.strftime("%I:%M%p").lstrip("0").lower()


def _build_response(
    question: Question,
    gps_point: GpsPoint,
    pois: list[dict],
    prior_answers: int = 0,
) -> dict:
    ts = gps_point.timestamp
    local_ts = _to_la_time(ts) if ts else None
    return {
        "question_id": str(question.id),
        "gps_point": {
            "lat": gps_point.lat,
            "lon": gps_point.lon,
            "timestamp": ts.isoformat() if ts else None,
            # Display only weekday + time (e.g. "Wednesday", "4:42pm").
            "weekday": local_ts.strftime("%A") if local_ts else None,
            "local_date": None,
            "local_time": _format_visit_time(local_ts) if local_ts else None,
        },
        "candidates": pois,
        "prior_answers": prior_answers,
    }


async def build_question_candidates(
    db: AsyncSession, lat: float, lon: float
) -> list[dict]:
    """The full candidate set frozen onto a question at creation.

    Deliberately unfiltered (no per-user exclusions), so it is a superset of
    anything any user is shown — displays are sliced from it, answers are
    validated against it, and exports can reconstruct the choice set.
    """
    return await get_nearby_pois(db, lat=lat, lon=lon, max_results=_MAX_FROZEN_CANDIDATES)


def _set_candidate_metadata(question: Question, candidates: list[dict]) -> None:
    question.candidates = candidates
    question.candidate_density = len(candidates)
    question.answers_target = settings.consensus_max_answers


async def ensure_question_candidates(
    db: AsyncSession, question: Question, gps_point: GpsPoint
) -> None:
    """Backfill the frozen candidate set on questions that predate it."""
    if question.candidates is not None:
        return
    candidates = await build_question_candidates(db, gps_point.lat, gps_point.lon)
    _set_candidate_metadata(question, candidates)
    await db.flush()


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
        h3_cell = gps_point.h3_cell or lat_lon_to_h3(gps_point.lat, gps_point.lon)
        question = Question(
            gps_point_id=gps_point.id,
            h3_cell=h3_cell,
            status="active",
        )
        candidates = await build_question_candidates(db, gps_point.lat, gps_point.lon)
        _set_candidate_metadata(question, candidates)
        db.add(question)
        await db.flush()
    else:
        await ensure_question_candidates(db, question, gps_point)

    return question
