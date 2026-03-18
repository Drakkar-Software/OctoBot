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

"""Shared fixtures for e2e tests."""

import os
import time
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import tests.mock_chain as mock_chain_module

ADMIN_PUBKEY = "0xE2eAdminPubkey"
USER_PUBKEY = "0xE2eUserPubkey"
OTHER_PUBKEY = "0xE2eOtherPubkey"
CHAIN_ID = "mock"

COLLECTIONS_PATH = str(Path(__file__).resolve().parent.parent / "fixtures" / "collections.json")


@pytest.fixture
async def s3_store():
    from starfish_server.storage.s3 import S3ObjectStore, S3StorageOptions

    store = S3ObjectStore(
        S3StorageOptions(
            access_key_id=os.environ["S3_ACCESS_KEY"],
            secret_access_key=os.environ["S3_SECRET_KEY"],
            endpoint=os.environ["S3_ENDPOINT"],
            bucket=os.environ.get("S3_BUCKET", "octobot-sync-test"),
            region=os.environ.get("S3_REGION", "us-east-1"),
        )
    )
    yield store
    try:
        for prefix in ("test/", "products/", "users/", "public/", "platform/"):
            keys = await store.list_keys(prefix)
            if keys:
                await store.delete_many(keys)
    finally:
        await store.close()


@pytest.fixture
def mock_chain():
    return mock_chain_module.MockChain(CHAIN_ID)


@pytest.fixture
def app(s3_store, mock_chain, monkeypatch):
    monkeypatch.setenv("PLATFORM_PUBKEY_EVM", ADMIN_PUBKEY)
    monkeypatch.setenv("ENCRYPTION_SECRET", "e2e-encryption-secret")
    monkeypatch.setenv("PLATFORM_ENCRYPTION_SECRET", "e2e-platform-secret")
    registry = chain.ChainRegistry()
    registry.register(mock_chain)
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    return sync_app.create_app(nonce, s3_store, registry, collections_path=COLLECTIONS_PATH)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def make_verify_headers(
    mock_chain: mock_chain_module.MockChain,
    pubkey: str,
    original_method: str,
    original_uri: str,
) -> dict[str, str]:
    """Build valid auth + nginx headers for the /verify endpoint."""
    ts = str(int(time.time() * 1000))
    nonce = f"e2e-nonce-{time.time()}"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical(
        original_method, original_uri, ts, nonce, body_hash
    )
    signature = f"e2e-sig-{ts}"
    mock_chain.set_signature_valid(canonical, signature, pubkey, True)

    return {
        constants.HEADER_PUBKEY: pubkey,
        constants.HEADER_SIGNATURE: signature,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce,
        constants.HEADER_CHAIN: CHAIN_ID,
        constants.HEADER_ORIGINAL_METHOD: original_method,
        constants.HEADER_ORIGINAL_URI: original_uri,
    }
