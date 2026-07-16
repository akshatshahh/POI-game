"""Tests for scoring and the consensus engine."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, GpsPoint, Question, User
from app.services.scoring_service import (
    BASE_POINTS,
    CONSENSUS_BONUS,
    DIFFICULTY_BONUS,
    STATUS_CONSENSUS,
    STATUS_NO_CONSENSUS,
    apply_initial_score,
    evaluate_consensus,
)


def test_apply_initial_score_is_participation_only() -> None:
    answer = Answer(
        question_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        selected_poi_id="poi-a",
    )
    total = apply_initial_score(answer, distance_meters=40.0)

    assert total == BASE_POINTS
    assert answer.base_points == BASE_POINTS
    assert answer.distance_bonus == 0  # proximity must not affect score
    assert answer.consensus_bonus == 0
    assert answer.selected_distance_meters == 40.0  # kept as ML covariate


async def _make_question(db: AsyncSession, answers_target: int = 3) -> Question:
    gps = GpsPoint(lat=34.0, lon=-118.0)
    db.add(gps)
    await db.flush()
    question = Question(
        gps_point_id=gps.id,
        status="active",
        candidates=[
            {"id": "poi-a", "name": "A", "category": "cafe", "lat": 34.0, "lon": -118.0, "distance_meters": 10.0},
            {"id": "poi-b", "name": "B", "category": "bar", "lat": 34.0, "lon": -118.0, "distance_meters": 20.0},
        ],
        candidate_density=2,
        answers_target=answers_target,
    )
    db.add(question)
    await db.flush()
    return question


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


async def _vote(db: AsyncSession, question: Question, user: User, poi_id: str) -> Answer:
    answer = Answer(question_id=question.id, user_id=user.id, selected_poi_id=poi_id)
    user.score += apply_initial_score(answer, distance_meters=10.0)
    db.add(answer)
    await db.flush()
    await evaluate_consensus(db, question)
    return answer


@pytest.mark.asyncio
async def test_unanimous_three_votes_reach_consensus_and_lock(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(3)]

    a1 = await _vote(db_session, question, users[0], "poi-a")
    assert question.status == "active"  # one vote is not evidence
    assert a1.consensus_bonus == 0

    await _vote(db_session, question, users[1], "poi-a")
    assert question.status == "active"  # 2-0 is below the minimum of 3 votes

    a3 = await _vote(db_session, question, users[2], "poi-a")
    assert question.status == STATUS_CONSENSUS
    assert question.locked_at is not None
    assert question.consensus_poi_id == "poi-a"
    assert question.consensus_confidence == 1.0
    assert question.votes_total == 3

    # Bonus paid exactly once, at lock, to every matching answer.
    assert a1.consensus_bonus == CONSENSUS_BONUS
    assert a3.score_awarded == BASE_POINTS + CONSENSUS_BONUS
    assert users[0].score == BASE_POINTS + CONSENSUS_BONUS


@pytest.mark.asyncio
async def test_disagreement_escalates_then_locks_without_consensus(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(5)]

    await _vote(db_session, question, users[0], "poi-a")
    await _vote(db_session, question, users[1], "poi-a")
    await _vote(db_session, question, users[2], "poi-b")
    # 2-1 at the base target: not decisive (lead < 2) → escalate, stay open.
    assert question.status == "active"
    assert question.answers_target == 5

    await _vote(db_session, question, users[3], "poi-b")  # 2-2 tie: keep collecting
    assert question.status == "active"

    a5 = await _vote(db_session, question, users[4], "poi-b")
    # 3-2 at the escalated cap: 60% but lead 1 → documented ambiguous point.
    assert question.status == STATUS_NO_CONSENSUS
    assert question.locked_at is not None
    assert question.consensus_poi_id is None
    assert question.consensus_confidence == 0.6
    # No consensus → nobody gets a bonus.
    assert a5.consensus_bonus == 0
    assert users[0].score == BASE_POINTS


@pytest.mark.asyncio
async def test_decisive_majority_after_escalation_pays_difficulty_bonus(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(4)]

    await _vote(db_session, question, users[0], "poi-a")
    await _vote(db_session, question, users[1], "poi-a")
    await _vote(db_session, question, users[2], "poi-b")  # 2-1 → escalate
    assert question.answers_target == 5

    a4 = await _vote(db_session, question, users[3], "poi-a")
    # 3-1: 75% with lead 2 → consensus before exhausting the cap.
    assert question.status == STATUS_CONSENSUS
    assert question.consensus_poi_id == "poi-a"
    assert question.consensus_confidence == 0.75
    # Escalated questions pay the difficulty bonus on top.
    assert a4.consensus_bonus == CONSENSUS_BONUS + DIFFICULTY_BONUS
    assert users[3].score == BASE_POINTS + CONSENSUS_BONUS + DIFFICULTY_BONUS
    # The dissenter keeps participation points only.
    assert users[2].score == BASE_POINTS


@pytest.mark.asyncio
async def test_locked_question_is_immutable(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(4)]
    for user in users[:3]:
        await _vote(db_session, question, user, "poi-a")
    assert question.status == STATUS_CONSENSUS
    locked_at = question.locked_at

    # A stray re-evaluation must not change anything.
    await evaluate_consensus(db_session, question)
    assert question.locked_at == locked_at
    assert question.consensus_poi_id == "poi-a"
