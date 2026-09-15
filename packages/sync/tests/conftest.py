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

"""Shared test fixtures."""

import os
import sys

import pytest

_OCTOBOT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_TESTS_ROOT = os.path.join(_OCTOBOT_ROOT, "tests")
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

from test_utils.journal_integration_fixtures import (
    isolated_journal_environment_context,
    surface_journal_errors_context,
)
from test_utils.journal_test_support import (
    disabled_node_journal_environment,
    enabled_node_journal_environment,
)

pytest_plugins = ("test_utils.journal_integration_fixtures",)


def _is_sync_journal_integration_test(request) -> bool:
    return request.node.path.name.endswith("_journal.py")


@pytest.fixture(autouse=True)
def disable_node_journal(request):
    if _is_sync_journal_integration_test(request):
        yield
        return
    with disabled_node_journal_environment():
        yield


@pytest.fixture(autouse=True)
def sync_journal_integration_autouse(request):
    if not _is_sync_journal_integration_test(request):
        yield
        return
    journal_user_root = request.getfixturevalue("journal_user_root")
    with enabled_node_journal_environment():
        with isolated_journal_environment_context(str(journal_user_root)):
            with surface_journal_errors_context():
                yield


class MemoryObjectStore:
    """Minimal AbstractObjectStore for testing."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get_string(self, key: str) -> str | None:
        return self._store.get(key)

    async def put(
        self, key: str, body: str, *, content_type: str | None = None, cache_control: str | None = None
    ) -> None:
        self._store[key] = body

    async def list_keys(
        self, prefix: str, *, start_after: str | None = None, limit: int | None = None
    ) -> list[str]:
        keys = sorted(k for k in self._store if k.startswith(prefix))
        if start_after:
            keys = [k for k in keys if k > start_after]
        if limit:
            keys = keys[:limit]
        return keys

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_many(self, keys: list[str]) -> None:
        for k in keys:
            self._store.pop(k, None)
