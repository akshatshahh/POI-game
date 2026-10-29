"""Tests for scoring and average pairwise Jaccard agreement."""

import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Answer, GpsPoint, Question, User
from app.services.scoring_service import (
    BASE_POINTS,
    STATUS_NO_CONSENSUS,
    answer_selection_set,
    apply_initial_score,
    evaluate_consensus,
    mean_pairwise_jaccard,
)


def test_apply_initial_score_is_participation_only() -> None:
    answer = Answer(
        question_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        selected_poi_id="poi-a",
        selected_poi_ids=["poi-a"],
    )
    total = apply_initial_score(answer, distance_meters=40.0)

    assert total == BASE_POINTS
    assert answer.base_points == BASE_POINTS
    assert answer.distance_bonus == 0  # proximity must not affect score
    assert answer.consensus_bonus == 0
    assert answer.selected_distance_meters == 40.0  # kept as ML covariate


def test_mean_pairwise_jaccard_owner_example() -> None:
    sets = [
        {"McDonald's", "Starbucks"},
        {"McDonald's", "Starbucks"},
        {"McDonald's"},
    ]
    assert mean_pairwise_jaccard(sets) == pytest.approx(2 / 3)


def test_mean_pairwise_jaccard_identical_sets_are_one() -> None:
    assert mean_pairwise_jaccard([{"a", "b"}, {"b", "a"}]) == 1.0
    assert mean_pairwise_jaccard([{"a"}, {"a"}, {"a"}]) == 1.0


def test_mean_pairwise_jaccard_disjoint_sets_are_zero() -> None:
    assert mean_pairwise_jaccard([{"a"}, {"b"}]) == 0.0


def test_mean_pairwise_jaccard_undefined_below_two_sets() -> None:
    assert mean_pairwise_jaccard([]) is None
    assert mean_pairwise_jaccard([{"a"}]) is None


def test_answer_selection_set_falls_back_to_primary() -> None:
    answer = Answer(
        question_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        selected_poi_id="poi-a",
        selected_poi_ids=None,
    )
    assert answer_selection_set(answer) == {"poi-a"}


async def _make_question(db: AsyncSession) -> Question:
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
        answers_target=settings.consensus_max_answers,
    )
    db.add(question)
    await db.flush()
    return question


async def _make_user(db: AsyncSession, name: str, **kwargs) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{name}@example.com",
        display_name=name,
        score=0,
        answers_count=0,
        **kwargs,
    )
    db.add(user)
    await db.flush()
    return user


async def _vote(
    db: AsyncSession, question: Question, user: User, poi_ids: str | list[str]
) -> Answer:
    if isinstance(poi_ids, str):
        poi_ids = [poi_ids]
    answer = Answer(
        question_id=question.id,
        user_id=user.id,
        selected_poi_id=poi_ids[0],
        selected_poi_ids=list(poi_ids),
    )
    user.score += apply_initial_score(answer, distance_meters=10.0)
    db.add(answer)
    await db.flush()
    await evaluate_consensus(db, question)
    return answer


@pytest.mark.asyncio
async def test_unanimous_answers_stay_open_until_the_cap(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(9)]

    a1 = await _vote(db_session, question, users[0], "poi-a")
    assert question.status == "active"
    assert a1.consensus_bonus == 0
    assert question.consensus_confidence is None  # one set has no pairs

    await _vote(db_session, question, users[1], "poi-a")
    assert question.status == "active"
    assert question.consensus_confidence == 1.0
    assert question.consensus_poi_id is None

    for user in users[2:]:
        await _vote(db_session, question, user, "poi-a")
    assert question.status == "active"
    assert question.votes_total == 9
    assert question.locked_at is None
    assert users[0].score == BASE_POINTS


@pytest.mark.asyncio
async def test_tenth_answer_locks_without_a_named_place_or_bonus(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(10)]
    for user in users[:9]:
        await _vote(db_session, question, user, ["poi-a", "poi-b"])

    a10 = await _vote(db_session, question, users[9], ["poi-a", "poi-b"])
    assert question.status == STATUS_NO_CONSENSUS
    assert question.locked_at is not None
    assert question.consensus_poi_id is None
    assert question.consensus_confidence == 1.0
    assert question.votes_total == 10
    assert a10.consensus_bonus == 0
    assert users[0].score == BASE_POINTS


@pytest.mark.asyncio
async def test_owner_example_jaccard_is_stored_before_lock(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(3)]

    await _vote(db_session, question, users[0], ["poi-a", "poi-b"])
    await _vote(db_session, question, users[1], ["poi-a", "poi-b"])
    await _vote(db_session, question, users[2], ["poi-a"])

    assert question.status == "active"
    assert question.consensus_poi_id is None
    assert question.consensus_confidence == pytest.approx(round(2 / 3, 4))
    assert question.votes_total == 3
    assert question.answers_target == 10


@pytest.mark.asyncio
async def test_disjoint_sets_store_zero_jaccard_and_stay_open(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(2)]
    await _vote(db_session, question, users[0], "poi-a")
    await _vote(db_session, question, users[1], "poi-b")
    assert question.status == "active"
    assert question.consensus_poi_id is None
    assert question.consensus_confidence == 0.0
    assert question.locked_at is None


@pytest.mark.asyncio
async def test_legacy_three_answer_target_is_raised_to_ten(db_session) -> None:
    gps = GpsPoint(lat=34.0, lon=-118.0)
    db_session.add(gps)
    await db_session.flush()
    question = Question(
        gps_point_id=gps.id,
        status="active",
        candidates=[
            {"id": "poi-a", "name": "A", "category": "cafe", "lat": 34.0, "lon": -118.0, "distance_meters": 10.0},
            {"id": "poi-b", "name": "B", "category": "bar", "lat": 34.0, "lon": -118.0, "distance_meters": 20.0},
        ],
        candidate_density=2,
        answers_target=3,
    )
    db_session.add(question)
    await db_session.flush()
    user = await _make_user(db_session, "legacy")
    await _vote(db_session, question, user, "poi-a")
    assert question.answers_target == 10
    assert question.status == "active"


@pytest.mark.asyncio
async def test_locked_question_is_immutable(db_session) -> None:
    question = await _make_question(db_session)
    users = [await _make_user(db_session, f"u{i}") for i in range(11)]
    for user in users[:10]:
        await _vote(db_session, question, user, "poi-a")
    assert question.status == STATUS_NO_CONSENSUS
    locked_at = question.locked_at
    confidence = question.consensus_confidence

    await evaluate_consensus(db_session, question)
    assert question.locked_at == locked_at
    assert question.consensus_poi_id is None
    assert question.consensus_confidence == confidence


@pytest.mark.asyncio
async def test_young_accounts_do_not_count_toward_jaccard_or_the_cap(
    db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "consensus_min_account_age_minutes", 60)
    question = await _make_question(db_session)
    old_users = [
        await _make_user(
            db_session,
            f"old{i}",
            created_at=datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=2),
        )
        for i in range(9)
    ]
    young = await _make_user(db_session, "young")
    for user in old_users:
        await _vote(db_session, question, user, "poi-a")
    await _vote(db_session, question, young, "poi-b")

    assert question.status == "active"
    assert question.votes_total == 9
    assert question.locked_at is None
    assert question.consensus_confidence == 1.0
    assert young.score == BASE_POINTS
