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
TEST_ADMIN_PUBKEY = "0xAdminPubkey1234567890abcdef"
TEST_CHAIN_ID = "mock"


class MockVerifyFn:
    """Async signature verifier backed by a set of valid (canonical, sig, pubkey) tuples."""

    def __init__(self) -> None:
        self._valid: dict[str, bool] = {}

    def set_valid(self, canonical: str, signature: str, pubkey: str, valid: bool = True) -> None:
        self._valid[f"{canonical}:{signature}:{pubkey}"] = valid

    async def __call__(self, canonical: str, signature: str, pubkey: str) -> bool:
        return self._valid.get(f"{canonical}:{signature}:{pubkey}", False)


@pytest.fixture
def memory_storage():
    return auth.MemoryStorageAdapter()


@pytest.fixture
def nonce_store(memory_storage):
    return auth.NonceStore(memory_storage)


@pytest.fixture
def mock_verify_fn():
    return MockVerifyFn()


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
    mock_verify: MockVerifyFn,
    pubkey: str = TEST_PUBKEY,
    method: str = "GET",
    path: str = "/",
    body: str = "",
    chain_id: str = TEST_CHAIN_ID,
) -> dict[str, str]:
    """Create valid auth headers and configure the mock verify fn to accept them."""
    ts = str(int(time.time() * 1000))
    nonce = f"test-nonce-{time.time()}"
    body_hash = auth.hash_body(body)
    canonical = auth.build_canonical(method, path, ts, nonce, body_hash)
    signature = f"sig-{ts}"

    mock_verify.set_valid(canonical, signature, pubkey)

    return {
        constants.HEADER_PUBKEY: pubkey,
        constants.HEADER_SIGNATURE: signature,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce,
        constants.HEADER_CHAIN: chain_id,
    }
