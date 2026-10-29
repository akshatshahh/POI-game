import pytest
from sqlalchemy import func, select

from app.models import CampaignSubscription
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_campaign_subscription_status_save_repeat_and_remove(
    client, test_user, db_session
):
    headers = auth_headers(test_user)

    initial = await client.get("/campaign-subscriptions/me", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "subscribed": False,
        "email": None,
        "created_at": None,
    }

    response = await client.post(
        "/campaign-subscriptions",
        headers=headers,
        json={"email": "  TEST@example.com  "},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"

    saved = (await db_session.execute(select(CampaignSubscription))).scalar_one()
    assert saved.user_id == test_user.id
    assert saved.email == "test@example.com"
    assert saved.consent_version == "campaign-notification-v1"

    status = await client.get("/campaign-subscriptions/me", headers=headers)
    assert status.status_code == 200
    assert status.json()["subscribed"] is True
    assert status.json()["email"] == "test@example.com"
    assert status.json()["created_at"] is not None

    repeated = await client.post(
        "/campaign-subscriptions",
        headers=headers,
        json={"email": "test@example.com"},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == response.json()["id"]
    count = await db_session.scalar(select(func.count(CampaignSubscription.id)))
    assert count == 1

    removed = await client.delete("/campaign-subscriptions/me", headers=headers)
    assert removed.status_code == 204
    assert removed.content == b""
    assert await db_session.scalar(select(func.count(CampaignSubscription.id))) == 0

    removed_again = await client.delete("/campaign-subscriptions/me", headers=headers)
    assert removed_again.status_code == 204
    final_status = await client.get("/campaign-subscriptions/me", headers=headers)
    assert final_status.json()["subscribed"] is False


@pytest.mark.asyncio
async def test_campaign_subscription_only_accepts_account_email(
    client, test_user
):
    response = await client.post(
        "/campaign-subscriptions",
        headers=auth_headers(test_user),
        json={"email": "different@example.com"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Use the email address associated with your account"
    )


@pytest.mark.asyncio
async def test_campaign_subscription_requires_auth_and_valid_email(client, test_user):
    assert (await client.get("/campaign-subscriptions/me")).status_code == 401
    assert (
        await client.post(
            "/campaign-subscriptions", json={"email": "test@example.com"}
        )
    ).status_code == 401
    assert (await client.delete("/campaign-subscriptions/me")).status_code == 401
    assert (
        await client.post(
            "/campaign-subscriptions",
            headers=auth_headers(test_user),
            json={"email": "not-an-email"},
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_campaign_subscriptions_do_not_appear_in_research_exports(
    client, test_user, admin_user
):
    response = await client.post(
        "/campaign-subscriptions",
        headers=auth_headers(test_user),
        json={"email": test_user.email},
    )
    assert response.status_code == 201

    for export in ("labels", "consensus"):
        result = await client.get(
            f"/admin/export/{export}?format=json",
            headers=auth_headers(admin_user),
        )
        assert result.status_code == 200
        assert result.json() == []
