import pytest
from sqlalchemy import select

from app.models import Feedback
from app.routers.feedback_router import feedback_rate_limiter
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def reset_feedback_limit():
    feedback_rate_limiter._hits.clear()
    yield
    feedback_rate_limiter._hits.clear()


@pytest.mark.asyncio
async def test_feedback_saved_separately(client, test_user, admin_user, db_session):
    response = await client.post("/feedback", headers=auth_headers(test_user), json={
        "rating": 4, "comments": "  The choices overlap  ", "email": " Reply@Example.com "})
    assert response.status_code == 201
    assert set(response.json()) == {"id", "created_at"}
    saved = (await db_session.execute(select(Feedback))).scalar_one()
    assert (saved.rating, saved.comments, saved.email) == (4, "The choices overlap", "reply@example.com")
    assert test_user.score == 0
    assert (await client.get("/admin/feedback", headers=auth_headers(test_user))).status_code == 403
    records = await client.get("/admin/feedback", headers=auth_headers(admin_user))
    assert records.json()[0]["rating"] == 4
    for export in ("labels", "consensus"):
        result = await client.get(f"/admin/export/{export}?format=json", headers=auth_headers(admin_user))
        assert result.json() == []


@pytest.mark.asyncio
async def test_feedback_optional_fields_and_auth(client, test_user):
    assert (await client.post("/feedback", json={"rating": 5})).status_code == 401
    assert (await client.get("/admin/feedback")).status_code == 401
    assert (await client.post("/feedback", headers=auth_headers(test_user), json={"rating": 5})).status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"rating": 0}, {"rating": 6}, {"rating": 2.5}, {"rating": True}, {"rating": 3, "email": "invalid"}, {"rating": 3, "comments": "x" * 4001}])
async def test_feedback_validation(client, test_user, body):
    assert (await client.post("/feedback", headers=auth_headers(test_user), json=body)).status_code == 422


@pytest.mark.asyncio
async def test_feedback_rate_limit(client, test_user):
    for _ in range(5):
        assert (await client.post("/feedback", headers=auth_headers(test_user), json={"rating": 3})).status_code == 201
    assert (await client.post("/feedback", headers=auth_headers(test_user), json={"rating": 3})).status_code == 429
