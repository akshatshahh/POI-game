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
