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
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
from tests.conftest import MemoryObjectStore


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_SECRET", "test-encryption-secret")
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    store = MemoryObjectStore()
    return sync_app.create_app(nonce, store)


async def test_health_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
