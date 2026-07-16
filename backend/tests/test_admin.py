"""Tests for admin endpoints."""

import pytest
from httpx import AsyncClient

from app.models import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_bulk_import_requires_admin(client: AsyncClient, test_user: User) -> None:
    response = await client.post(
        "/admin/gps-points/bulk",
        json={"points": [{"lat": 34.0, "lon": -118.0}]},
        headers=auth_headers(test_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bulk_import_as_admin(client: AsyncClient, admin_user: User) -> None:
    response = await client.post(
        "/admin/gps-points/bulk",
        json={"points": [
            {"lat": 34.0, "lon": -118.0},
            {"lat": 34.1, "lon": -118.1, "source": "test"},
        ]},
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_export_labels_requires_admin(client: AsyncClient, test_user: User) -> None:
    response = await client.get(
        "/admin/export/labels",
        headers=auth_headers(test_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_export_labels_empty(client: AsyncClient, admin_user: User) -> None:
    response = await client.get(
        "/admin/export/labels?format=json",
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_export_consensus_includes_question_state(
    client: AsyncClient, admin_user: User, db_session
) -> None:
    from app.models import GpsPoint, Question

    gps = GpsPoint(lat=34.0, lon=-118.0)
    db_session.add(gps)
    await db_session.flush()
    db_session.add(Question(
        gps_point_id=gps.id,
        status="active",
        candidate_density=4,
        answers_target=3,
    ))
    await db_session.commit()

    response = await client.get(
        "/admin/export/consensus?format=json",
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    record = records[0]
    assert record["status"] == "active"
    assert record["consensus_poi_id"] is None
    assert record["candidate_density"] == 4
    assert record["answers_target"] == 3
    assert record["vote_distribution"] == {}
