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

"""Tests for nonce replay protection."""

import pytest

import octobot_sync.auth as auth


@pytest.fixture
def nonce_store():
    return auth.NonceStore(auth.MemoryStorageAdapter())


async def test_fresh_nonce_accepted(nonce_store):
    assert await nonce_store.nonce_insert("nonce1", "pubkey1") is True


async def test_duplicate_nonce_rejected(nonce_store):
    assert await nonce_store.nonce_insert("nonce1", "pubkey1") is True
    assert await nonce_store.nonce_insert("nonce1", "pubkey1") is False


async def test_same_nonce_different_pubkey(nonce_store):
    assert await nonce_store.nonce_insert("nonce1", "pubkey1") is True
    assert await nonce_store.nonce_insert("nonce1", "pubkey2") is True


async def test_different_nonces(nonce_store):
    assert await nonce_store.nonce_insert("nonce1", "pubkey1") is True
    assert await nonce_store.nonce_insert("nonce2", "pubkey1") is True
