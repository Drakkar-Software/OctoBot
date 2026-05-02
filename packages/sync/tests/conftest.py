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

import time

import pytest

import octobot_sync.auth as auth
import octobot_sync.constants as constants


TEST_PUBKEY = "0xTestPubkey1234567890abcdef"


@pytest.fixture
def memory_storage():
    return auth.MemoryStorageAdapter()


@pytest.fixture
def nonce_store(memory_storage):
    return auth.NonceStore(memory_storage)


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


@pytest.fixture
def memory_object_store():
    return MemoryObjectStore()


def make_auth_headers(
    pubkey: str = TEST_PUBKEY,
    method: str = "GET",
    path: str = "/",
    body: str = "",
) -> dict[str, str]:
    """Build auth headers with a deterministic fake signature.

    Callers must patch octobot_sync.chain.verify_evm to return True for the
    canonical string produced by these headers.
    """
    ts = str(int(time.time() * 1000))
    nonce = f"test-nonce-{time.time()}"
    body_hash = auth.hash_body(body)
    canonical = auth.build_canonical(method, path, ts, nonce, body_hash)
    signature = f"sig-{ts}"

    return {
        constants.HEADER_PUBKEY: pubkey,
        constants.HEADER_SIGNATURE: signature,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce,
    }, canonical, signature
