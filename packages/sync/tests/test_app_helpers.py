#  Drakkar-Software OctoBot-Sync
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

"""Tests for create_app."""

import pytest
from httpx import AsyncClient, ASGITransport

import octobot_sync.app as sync_app
from tests.conftest import MemoryObjectStore


@pytest.fixture
def app():
    store = MemoryObjectStore()
    return sync_app.create_app(store)


async def test_health_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_create_app_returns_signed_path_middleware(app):
    assert isinstance(app, sync_app.SignedPathMiddleware)


async def test_create_app_with_custom_collections_path():
    store = MemoryObjectStore()
    # Should not raise even with a non-existent collections path (falls back to default)
    created_app = sync_app.create_app(store, collections_path="/nonexistent/path.json")
    assert isinstance(created_app, sync_app.SignedPathMiddleware)


async def test_create_app_with_allowlist():
    store = MemoryObjectStore()
    # is_allowed_user_id callable accepted without error
    created_app = sync_app.create_app(store, is_allowed_user_id=lambda uid: True)
    assert isinstance(created_app, sync_app.SignedPathMiddleware)
