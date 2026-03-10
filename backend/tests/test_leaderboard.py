"""Tests for leaderboard endpoint."""

import pytest
from httpx import AsyncClient

from app.models import User


@pytest.mark.asyncio
async def test_leaderboard_empty(client: AsyncClient) -> None:
    response = await client.get("/leaderboard")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_leaderboard_with_users(client: AsyncClient, test_user: User, db_session) -> None:
    test_user.score = 50
    test_user.answers_count = 5
    await db_session.commit()

    response = await client.get("/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Test User"
    assert data[0]["score"] == 50
    assert data[0]["rank"] == 1
