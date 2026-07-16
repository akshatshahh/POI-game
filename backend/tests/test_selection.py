"""Tests for question selection: completion-first order and terminal exclusion."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, GpsPoint, Question, User
from app.services import question_service

# Inside the LA study-area bbox used by app.regions.
LA_LAT, LA_LON = 34.02, -118.28

FAKE_POIS = [
    {"id": "poi-a", "name": "A", "category": "cafe", "lat": LA_LAT, "lon": LA_LON, "distance_meters": 10.0},
    {"id": "poi-b", "name": "B", "category": "bar", "lat": LA_LAT, "lon": LA_LON, "distance_meters": 20.0},
    {"id": "poi-c", "name": "C", "category": "retail", "lat": LA_LAT, "lon": LA_LON, "distance_meters": 30.0},
]


async def _fake_nearby(db, lat, lon, radius_meters=None, max_results=None):
    return list(FAKE_POIS)


async def _make_user(db: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), email=f"{name}@example.com", display_name=name)
    db.add(user)
    await db.flush()
    return user


async def _make_point_with_question(
    db: AsyncSession, h3_cell: str
) -> tuple[GpsPoint, Question]:
    gps = GpsPoint(lat=LA_LAT, lon=LA_LON, h3_cell=h3_cell)
    db.add(gps)
    await db.flush()
    question = Question(
        gps_point_id=gps.id,
        h3_cell=h3_cell,
        status="active",
        candidates=list(FAKE_POIS),
        candidate_density=len(FAKE_POIS),
        answers_target=3,
    )
    db.add(question)
    await db.flush()
    return gps, question


@pytest.mark.asyncio
async def test_in_progress_questions_are_served_first(db_session, monkeypatch) -> None:
    """A point that already has answers must finish before fresh points start."""
    monkeypatch.setattr(question_service, "get_nearby_pois", _fake_nearby)

    _, q_in_progress = await _make_point_with_question(db_session, "89a-cell-a")
    await _make_point_with_question(db_session, "89a-cell-b")

    other = await _make_user(db_session, "other")
    db_session.add(Answer(question_id=q_in_progress.id, user_id=other.id, selected_poi_id="poi-a"))
    await db_session.flush()

    newcomer = await _make_user(db_session, "newcomer")
    result = await question_service.get_next_question(db_session, newcomer.id)

    assert result is not None
    assert result["question_id"] == str(q_in_progress.id)


@pytest.mark.asyncio
async def test_locked_questions_are_never_served(db_session, monkeypatch) -> None:
    monkeypatch.setattr(question_service, "get_nearby_pois", _fake_nearby)

    _, q_locked = await _make_point_with_question(db_session, "89a-cell-a")
    q_locked.status = "consensus_reached"
    await db_session.flush()
    _, q_open = await _make_point_with_question(db_session, "89a-cell-b")

    user = await _make_user(db_session, "player")
    result = await question_service.get_next_question(db_session, user.id)

    assert result is not None
    assert result["question_id"] == str(q_open.id)


@pytest.mark.asyncio
async def test_displayed_candidates_come_from_frozen_set(db_session, monkeypatch) -> None:
    """What the user sees must be a slice of the validated frozen set."""
    monkeypatch.setattr(question_service, "get_nearby_pois", _fake_nearby)

    _, question = await _make_point_with_question(db_session, "89a-cell-a")
    user = await _make_user(db_session, "player")

    result = await question_service.get_next_question(db_session, user.id)
    assert result is not None
    shown_ids = {c["id"] for c in result["candidates"]}
    frozen_ids = {c["id"] for c in question.candidates}
    assert shown_ids <= frozen_ids
    assert len(shown_ids) >= question_service.MIN_CANDIDATES
