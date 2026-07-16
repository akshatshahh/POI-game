"""Tests for game endpoints."""

import datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GpsPoint, Question, User
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
        answers_target=3,
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
        "selected_poi_id": "test-poi",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_answer_invalid_question(client: AsyncClient, test_user: User) -> None:
    response = await client.post(
        "/game/answer",
        json={
            "question_id": "00000000-0000-0000-0000-000000000000",
            "selected_poi_id": "test-poi",
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
        json={"question_id": str(question.id), "selected_poi_id": "poi-a"},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score_awarded"] == 5  # participation only; bonus waits for consensus
    assert data["selected_poi_id"] == "poi-a"

    await db_session.refresh(test_user)
    assert test_user.score == 5
    assert test_user.answers_count == 1


@pytest.mark.asyncio
async def test_submit_answer_rejects_poi_outside_frozen_candidates(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    response = await client.post(
        "/game/answer",
        json={"question_id": str(question.id), "selected_poi_id": "poi-nowhere"},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_answer_duplicate_returns_409(
    client: AsyncClient, test_user: User, db_session: AsyncSession
) -> None:
    question = await _make_question(db_session)
    payload = {"question_id": str(question.id), "selected_poi_id": "poi-a"}
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
        json={"question_id": str(question.id), "selected_poi_id": "poi-a"},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 409
    assert "finalized" in response.json()["detail"]
