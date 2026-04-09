"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient

from app.models import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_me_endpoint_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_authenticated(client: AsyncClient, test_user: User) -> None:
    response = await client.get("/auth/me", headers=auth_headers(test_user))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert data["score"] == 0


@pytest.mark.asyncio
async def test_google_login_redirects(client: AsyncClient) -> None:
    response = await client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    loc = response.headers.get("location", "")
    assert "accounts.google.com" in loc
    assert "state=" in loc


@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient) -> None:
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
