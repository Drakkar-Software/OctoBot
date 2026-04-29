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

"""Tests for MemoryStorageAdapter CRUD and TTL behaviour."""

import pytest

import octobot_sync.auth as auth


@pytest.fixture
def storage():
    return auth.MemoryStorageAdapter()


async def test_set_and_get(storage):
    await storage.set("k1", "v1")
    assert await storage.get("k1") == "v1"


async def test_get_missing_key(storage):
    assert await storage.get("nonexistent") is None


async def test_delete(storage):
    await storage.set("k1", "v1")
    await storage.delete("k1")
    assert await storage.get("k1") is None


async def test_delete_missing_key(storage):
    await storage.delete("nonexistent")  # should not raise


async def test_set_if_absent_existing(storage):
    await storage.set("k1", "original")
    result = await storage.set_if_absent("k1", "new", ttl_ms=60_000)
    assert result is False
    assert await storage.get("k1") == "original"


async def test_ttl_expiration(storage, monkeypatch):
    """Value disappears after TTL expires (monkeypatched time)."""
    import time as time_mod

    now = 1_000_000.0
    monkeypatch.setattr(time_mod, "time", lambda: now)

    await storage.set("k1", "v1", ttl_ms=5_000)
    assert await storage.get("k1") == "v1"

    # Advance past TTL
    monkeypatch.setattr(time_mod, "time", lambda: now + 6.0)
    assert await storage.get("k1") is None


async def test_get_expired_key_returns_none(storage, monkeypatch):
    """Expired entry is cleaned on read."""
    import time as time_mod

    now = 1_000_000.0
    monkeypatch.setattr(time_mod, "time", lambda: now)

    await storage.set_if_absent("k1", "v1", ttl_ms=1_000)
    monkeypatch.setattr(time_mod, "time", lambda: now + 2.0)

    assert await storage.get("k1") is None
    assert "k1" not in storage._store


async def test_cleanup_removes_expired_only(storage, monkeypatch):
    """_cleanup removes expired entries but keeps valid ones."""
    import time as time_mod

    now = 1_000_000.0
    monkeypatch.setattr(time_mod, "time", lambda: now)

    await storage.set("short", "v1", ttl_ms=1_000)
    await storage.set("long", "v2", ttl_ms=60_000)

    # Advance past short TTL but not long
    monkeypatch.setattr(time_mod, "time", lambda: now + 2.0)
    storage._cleanup()

    assert "short" not in storage._store
    assert await storage.get("long") == "v2"
