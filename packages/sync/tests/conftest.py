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

"""Shared test fixtures and module stubs.

Heavy OctoBot dependencies (supabase, numpy, octobot_node, octobot_protocol)
are not present in the sync-package venv. We install lightweight MagicMock
stubs into sys.modules here — before any test files are imported — so that
octobot_sync.app, octobot_sync.server, and octobot_sync.sync.* can be
collected and run without those optional runtime deps.
"""

import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# sys.modules stubs — must run at conftest import time (before test collection)
# ---------------------------------------------------------------------------


def _make_stub(name: str) -> MagicMock:
    m = MagicMock()
    m.__path__ = []        # marks it as a package so sub-imports don't fail
    m.__package__ = name
    m.__spec__ = None      # prevents importlib from treating it as real
    sys.modules[name] = m
    return m


_STUB_MODULES = [
    # OctoBot community (requires supabase_auth / numpy / sortedcontainers)
    "octobot",
    "octobot.community",
    "octobot.community.authentication",
    # octobot_protocol — node protocol models, not in sync venv
    "octobot_protocol",
    "octobot_protocol.models",
    # octobot_node — node-specific constants and protocol, not in sync venv
    "octobot_node",
    "octobot_node.constants",
    "octobot_node.protocol",
    "octobot_node.protocol.user_actions",
    "octobot_node.protocol.user_data",
    "octobot_node.protocol.accounts",
    "octobot_node.protocol.accounts_authentication",
    "octobot_node.protocol.accounts_trading",
]

for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        _make_stub(_mod_name)


# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------

import pytest


class MemoryObjectStore:
    """Minimal in-memory AbstractObjectStore for testing.

    All methods accept *context=None* so the Starfish router, which calls
    store methods with ``context=<StoreContext>``, doesn't get a TypeError.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get_string(self, key: str, *, context=None) -> str | None:
        return self._store.get(key)

    async def put(
        self,
        key: str,
        body: str,
        *,
        content_type: str | None = None,
        cache_control: str | None = None,
        context=None,
    ) -> None:
        self._store[key] = body

    async def list_keys(
        self,
        prefix: str,
        *,
        start_after: str | None = None,
        limit: int | None = None,
        context=None,
    ) -> list[str]:
        keys = sorted(k for k in self._store if k.startswith(prefix))
        if start_after:
            keys = [k for k in keys if k > start_after]
        if limit:
            keys = keys[:limit]
        return keys

    async def delete(self, key: str, *, context=None) -> None:
        self._store.pop(key, None)

    async def delete_many(self, keys: list[str], *, context=None) -> None:
        for k in keys:
            self._store.pop(k, None)


@pytest.fixture
def memory_object_store():
    return MemoryObjectStore()
