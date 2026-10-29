"""Tests for game endpoints."""

import datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models import Answer, GpsPoint, Question, User
from tests.conftest import auth_headers

CANDIDATES = [
    {"id": "poi-a", "name": "Cafe A", "category": "cafe", "lat": 34.0, "lon": -118.0, "distance_meters": 12.5},
    {"id": "poi-b", "name": "Bar B", "category": "bar", "lat": 34.0, "lon": -118.0, "distance_meters": 30.0},
    {"id": "poi-c", "name": "Shop C", "category": "retail", "lat": 34.0, "lon": -118.0, "distance_meters": 45.0},
]


async def _make_question(db: AsyncSession) -> Question:
    gps = GpsPoint(lat=34.0, lon=-118.0)
    db.add(gps)
    await db.flush()
    question = Question(
        gps_point_id=gps.id,
        status="active",
        candidates=CANDIDATES,
        candidate_density=len(CANDIDATES),
        answers_target=10,
    )
    db.add(question)
    await db.commit()
    return question


@pytest.mark.asyncio
async def test_next_question_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/game/next-question")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_next_question_no_gps_points(client: AsyncClient, test_user: User) -> None:
    response = await client.get("/game/next-question", headers=auth_headers(test_user))
    assert response.status_code == 404
    assert "No more questions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_answer_unauthenticated(client: AsyncClient) -> None:
    response = await client.post("/game/answer", json={
        "question_id": "00000000-0000-0000-0000-000000000000",
        "selected_poi_ids": ["test-poi"],
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_answer_invalid_question(client: AsyncClient, test_user: User) -> None:
    response = await client.post(
        "/game/answer",
        json={
            "question_id": "00000000-0000-0000-0000-000000000000",
            "selected_poi_ids": ["test-poi"],
        },
        headers=auth_headers(test_user),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_answer_happy_path(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-a"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score_awarded"] == 5  # participation only
    assert data["selected_poi_id"] == "poi-a"
    assert data["selected_poi_ids"] == ["poi-a"]

    await db_session.refresh(test_user)
    assert test_user.score == 5
    assert test_user.answers_count == 1


@pytest.mark.asyncio
async def test_submit_answer_multi_select(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-b", "poi-a", "poi-c"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["selected_poi_id"] == "poi-b"  # primary = first in list
    assert data["selected_poi_ids"] == ["poi-b", "poi-a", "poi-c"]
    assert data["score_awarded"] == 5


@pytest.mark.asyncio
async def test_submit_answer_deduplicates_poi_ids(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-a", "poi-a", "poi-b"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["selected_poi_ids"] == ["poi-a", "poi-b"]


@pytest.mark.asyncio
async def test_submit_answer_empty_list_returns_422(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": []},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answer_rejects_more_than_max_candidates(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    from app.config import settings

    question = await _make_question(db_session)
    too_many = [f"poi-{i}" for i in range(settings.poi_max_candidates + 1)]
    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": too_many},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answer_rejects_poi_outside_frozen_candidates(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-nowhere"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_answer_rejects_if_any_poi_invalid(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-a", "poi-nowhere"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_answer_duplicate_returns_409(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    payload = {"question_id": str(question.id), "selected_poi_ids": ["poi-a"]}
    first = await client.post("/game/answer", json=payload, headers=auth_headers(test_user))
    assert first.status_code == 200
    second = await client.post("/game/answer", json=payload, headers=auth_headers(test_user))
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_submit_answer_on_locked_question_returns_409(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    question.status = "consensus_reached"
    question.consensus_poi_id = "poi-a"
    question.locked_at = datetime.datetime.now(datetime.timezone.utc)
    await db_session.commit()

    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-a"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 409
    assert "finalized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenth_submit_completes_question_and_rejects_the_next(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    users = []
    for index in range(10):
        user = User(
            id=uuid.uuid4(),
            email=f"cap{index}@example.com",
            display_name=f"Cap {index}",
        )
        db_session.add(user)
        users.append(user)
    await db_session.commit()

    for user in users:
        response = await client.post(
            "/game/answer",
            json={"question_id": str(question.id), "selected_poi_ids": ["poi-a"]},
            headers=auth_headers(user),
        )
        assert response.status_code == 200
        assert response.json()["score_awarded"] == 5

    await db_session.refresh(question)
    assert question.status == "no_consensus"
    assert question.locked_at is not None
    assert question.consensus_poi_id is None
    assert question.answers_target == 10
    assert question.votes_total == 10

    extra = User(
        id=uuid.uuid4(),
        email="cap-extra@example.com",
        display_name="Cap Extra",
    )
    db_session.add(extra)
    await db_session.commit()
    blocked = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-a"]},
        headers=auth_headers(extra),
    )
    assert blocked.status_code == 409
    assert "finalized" in blocked.json()["detail"]


@pytest.mark.asyncio
async def test_submit_stores_client_displayed_poi_ids(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    shown = ["poi-c", "poi-a"]

    response = await client.post(
        "/game/answer",
        json={
            "question_id": str(question.id),
            "selected_poi_ids": ["poi-a"],
            "displayed_poi_ids": shown,
        },
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200

    stored = await db_session.execute(
        select(Answer).where(Answer.question_id == question.id)
    )
    assert stored.scalar_one().displayed_poi_ids == shown


@pytest.mark.asyncio
async def test_submit_without_displayed_ids_stores_the_recomputed_slice(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_ids": ["poi-b"]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200

    stored = await db_session.execute(
        select(Answer).where(Answer.question_id == question.id)
    )
    assert stored.scalar_one().displayed_poi_ids == ["poi-a", "poi-b", "poi-c"]


@pytest.mark.asyncio
async def test_submit_rejects_displayed_poi_outside_frozen_set(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={
            "question_id": str(question.id),
            "selected_poi_ids": ["poi-a"],
            "displayed_poi_ids": ["poi-a", "poi-nowhere"],
        },
        headers=auth_headers(test_user),
    )
    assert response.status_code == 400
    assert "Displayed POI" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_rejects_selected_poi_not_among_displayed(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)

    response = await client.post(
        "/game/answer",
        json={
            "question_id": str(question.id),
            "selected_poi_ids": ["poi-b"],
            "displayed_poi_ids": ["poi-a", "poi-c"],
        },
        headers=auth_headers(test_user),
    )
    assert response.status_code == 400
    assert "not among the places shown" in response.json()["detail"]
