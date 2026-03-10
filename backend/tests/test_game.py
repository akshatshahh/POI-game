"""Tests for game endpoints."""

import pytest
from httpx import AsyncClient

from app.models import User
from tests.conftest import auth_headers


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
