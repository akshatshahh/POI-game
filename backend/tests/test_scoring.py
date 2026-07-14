"""Tests for scoring logic."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, GpsPoint, Question, User
from app.services.scoring_service import (
    BASE_POINTS,
    CONSENSUS_BONUS,
    apply_initial_score,
    distance_bonus,
    retroactive_score_update,
)


def test_distance_bonus_tiers() -> None:
    assert distance_bonus(0) == 5
    assert distance_bonus(50) == 5
    assert distance_bonus(51) == 4
    assert distance_bonus(100) == 4
    assert distance_bonus(200) == 3
    assert distance_bonus(350) == 2
    assert distance_bonus(351) == 1
    assert distance_bonus(10_000) == 1


def test_apply_initial_score_sets_components() -> None:
    answer = Answer(
        question_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        selected_poi_id="poi-a",
    )
    total = apply_initial_score(answer, distance_meters=40)

    assert answer.base_points == BASE_POINTS
    assert answer.distance_bonus == 5
    assert answer.consensus_bonus == 0
    assert answer.score_awarded == BASE_POINTS + 5
    assert total == answer.score_awarded


async def _make_user(db: AsyncSession, name: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{name}@example.com",
        display_name=name,
        score=0,
        answers_count=0,
    )
    db.add(user)
    await db.flush()
    return user


async def _answer(
    db: AsyncSession, question: Question, user: User, poi_id: str
) -> Answer:
    answer = Answer(
        question_id=question.id,
        user_id=user.id,
        selected_poi_id=poi_id,
    )
    user.score += apply_initial_score(answer, distance_meters=40)
    db.add(answer)
    await db.flush()
    return answer


@pytest.mark.asyncio
async def test_consensus_bonus_awarded_and_revoked(db_session: AsyncSession) -> None:
    gps = GpsPoint(lat=34.0, lon=-118.0)
    db_session.add(gps)
    await db_session.flush()
    question = Question(gps_point_id=gps.id, status="active")
    db_session.add(question)
    await db_session.flush()

    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    # One answer: no consensus yet.
    a_alice = await _answer(db_session, question, alice, "poi-a")
    await retroactive_score_update(db_session, question.id)
    assert a_alice.consensus_bonus == 0

    # Second matching answer: both earn the bonus.
    a_bob = await _answer(db_session, question, bob, "poi-a")
    await retroactive_score_update(db_session, question.id)
    assert a_alice.consensus_bonus == CONSENSUS_BONUS
    assert a_bob.consensus_bonus == CONSENSUS_BONUS
    assert alice.score == a_alice.score_awarded
    assert a_alice.score_awarded == BASE_POINTS + a_alice.distance_bonus + CONSENSUS_BONUS

    # Three players pick a different POI: consensus shifts, bonus is revoked.
    for name in ("carol", "dave", "erin"):
        user = await _make_user(db_session, name)
        await _answer(db_session, question, user, "poi-b")
    await retroactive_score_update(db_session, question.id)

    assert a_alice.consensus_bonus == 0
    assert a_bob.consensus_bonus == 0
    assert alice.score == BASE_POINTS + a_alice.distance_bonus
