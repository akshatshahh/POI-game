"""Service for selecting and creating game questions."""

import datetime
import uuid
import zoneinfo

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.geo import lat_lon_to_h3
from app.models import Answer, GpsPoint, Question
from app.regions import point_in_los_angeles
from app.services.poi_service import get_nearby_pois
from app.services.scoring_service import TERMINAL_STATUSES

# Question timestamps are shown in study-area local time (the game covers LA).
_LA_TZ = zoneinfo.ZoneInfo("America/Los_Angeles")

# A question needs at least this many candidate POIs to be playable.
# Answer validation in game_router uses the same threshold.
MIN_CANDIDATES = 3

# Hard cap on how many POIs one oversampling query may fetch.
_MAX_OVERSAMPLE = 400

# How many low-answer-count GPS points to try before giving up on a question.
_GPS_SAMPLE_SIZE = 5


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
        cap = min(max(max_out * mult, min_needed * mult), _MAX_OVERSAMPLE)
        pois = await get_nearby_pois(db, lat=lat, lon=lon, max_results=cap)
        filtered = [p for p in pois if p["id"] not in excluded]
        if len(filtered) >= min_needed:
            return filtered[:max_out]
        if cap == _MAX_OVERSAMPLE:
            # Already fetched at the cap; a larger multiplier can't help.
            break
    return []


async def get_next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int = MIN_CANDIDATES,
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


async def _next_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    min_candidates: int,
    exclusion: list[ColumnElement],
) -> dict | None:
    """Pick the next eligible GPS point, completion-first.

    Points that already have answers come first (most answers first), so
    in-progress questions reach their consensus target and produce a usable
    label before annotator effort is spread onto fresh points. Terminal
    questions are excluded upstream, so "most answers" never means "done".
    """
    answer_count = (
        select(func.count(Answer.id))
        .join(Question, Question.id == Answer.question_id)
        .where(Question.gps_point_id == GpsPoint.id)
        .correlate(GpsPoint)
        .scalar_subquery()
    )

    in_progress_first = case((answer_count > 0, 0), else_=1)

    stmt = (
        select(GpsPoint)
        .where(*exclusion)
        .order_by(in_progress_first, answer_count.desc(), func.random())
        .limit(_GPS_SAMPLE_SIZE)
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
    local_ts = _to_la_time(ts) if ts else None
    return {
        "question_id": str(question.id),
        "gps_point": {
            "lat": gps_point.lat,
            "lon": gps_point.lon,
            "timestamp": ts.isoformat() if ts else None,
            "weekday": local_ts.strftime("%A") if local_ts else None,
            "local_date": local_ts.strftime("%B %d, %Y") if local_ts else None,
            "local_time": local_ts.strftime("%I:%M %p") if local_ts else None,
        },
        "candidates": pois,
    }


async def build_question_candidates(
    db: AsyncSession, lat: float, lon: float
) -> list[dict]:
    """The full candidate set frozen onto a question at creation.

    Deliberately unfiltered (no per-user exclusions) and capped only by the
    oversampling limit, so it is a superset of anything any user is shown —
    answers can be validated against it, and exports can reconstruct the
    choice set.
    """
    return await get_nearby_pois(db, lat=lat, lon=lon, max_results=_MAX_OVERSAMPLE)


def _set_candidate_metadata(question: Question, candidates: list[dict]) -> None:
    question.candidates = candidates
    question.candidate_density = len(candidates)
    # Dense areas are harder to annotate reliably: raise the annotation
    # target up front instead of waiting for disagreement.
    if question.candidate_density >= settings.dense_candidate_threshold:
        question.answers_target = settings.consensus_max_target
    else:
        question.answers_target = settings.consensus_base_target


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
