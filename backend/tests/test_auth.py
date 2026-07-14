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


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _fake_google_client(userinfo: dict) -> type:
    """AsyncClient stand-in that returns a canned token and userinfo."""

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *exc) -> bool:
            return False

        async def post(self, url: str, data: dict | None = None) -> _FakeResponse:
            return _FakeResponse({"access_token": "fake-token"})

        async def get(self, url: str, headers: dict | None = None) -> _FakeResponse:
            return _FakeResponse(userinfo)

    return _FakeClient


async def _google_callback(client: AsyncClient, monkeypatch, userinfo: dict):
    monkeypatch.setattr(
        "app.routers.auth_router.httpx.AsyncClient", _fake_google_client(userinfo)
    )
    client.cookies.set("oauth_state", "state123")
    return await client.get(
        "/auth/google/callback?code=abc&state=state123", follow_redirects=False
    )


@pytest.mark.asyncio
async def test_google_callback_creates_new_user(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    response = await _google_callback(client, monkeypatch, {
        "id": "google-new",
        "email": "new@example.com",
        "verified_email": True,
        "name": "New User",
    })
    assert response.status_code == 307
    assert "error" not in response.headers["location"]

    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.email == "new@example.com"))
    user = result.scalar_one()
    assert user.google_id == "google-new"


@pytest.mark.asyncio
async def test_google_callback_refuses_to_link_password_account(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    """A password-only account must not be capturable via Google sign-in
    with the same (unverified at registration) email."""
    import uuid

    victim = User(
        id=uuid.uuid4(),
        username="victim",
        email="victim@example.com",
        display_name="Victim",
        password_hash="not-a-real-hash",
    )
    db_session.add(victim)
    await db_session.commit()

    response = await _google_callback(client, monkeypatch, {
        "id": "google-victim",
        "email": "victim@example.com",
        "verified_email": True,
        "name": "Someone",
    })
    assert response.status_code == 307
    assert "error=email_in_use" in response.headers["location"]

    await db_session.refresh(victim)
    assert victim.google_id is None
