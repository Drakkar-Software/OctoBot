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

"""E2E tests — error sharing via sync server + real S3."""

import os
import time
import uuid

import pytest
from httpx import ASGITransport

from satellite_sdk import SatelliteClient, SyncManager

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import tests.mock_chain as mock_chain_module
from octobot.community.errors_upload.error_sharing import (
    upload_error,
    ERRORS_PULL_PATH_TEMPLATE,
    ERRORS_PUSH_PATH_TEMPLATE,
    ENCRYPTION_INFO,
)
from tests.e2e.conftest import ADMIN_PUBKEY, USER_PUBKEY, CHAIN_ID, COLLECTIONS_PATH

pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_ENDPOINT"),
    reason="S3_ENDPOINT not set — skipping e2e tests",
)


def _make_auth_provider(
    mock_chain: mock_chain_module.MockChain,
    pubkey: str,
):
    async def auth_provider(
        *, method: str, path: str, body: str | None
    ) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        nonce = f"err-nonce-{uuid.uuid4()}"
        body_hash = auth.hash_body(body or "")
        canonical = auth.build_canonical(method, path, ts, nonce, body_hash)
        signature = f"err-sig-{ts}"
        mock_chain.set_signature_valid(canonical, signature, pubkey, True)

        return {
            constants.HEADER_PUBKEY: pubkey,
            constants.HEADER_SIGNATURE: signature,
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: nonce,
            constants.HEADER_CHAIN: CHAIN_ID,
        }

    return auth_provider


@pytest.fixture
async def sync_client(s3_store, mock_chain, monkeypatch):
    monkeypatch.setenv("PLATFORM_PUBKEY_EVM", ADMIN_PUBKEY)
    monkeypatch.setenv("ENCRYPTION_SECRET", "e2e-encryption-secret")
    monkeypatch.setenv("PLATFORM_ENCRYPTION_SECRET", "e2e-platform-secret")
    registry = chain.ChainRegistry()
    registry.register(mock_chain)
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    app = sync_app.create_app(nonce, s3_store, registry, collections_path=COLLECTIONS_PATH)

    import httpx

    transport = ASGITransport(app=app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    client = SatelliteClient(
        base_url="http://test",
        auth=_make_auth_provider(mock_chain, USER_PUBKEY),
        client=http_client,
    )
    yield client
    await client.close()


async def test_upload_error_returns_credentials(sync_client):
    """upload_error returns errorId (salt) and errorSecret for decryption."""
    try:
        raise ValueError("something broke during trading")
    except ValueError as exc:
        result = await upload_error(
            sync_client,
            USER_PUBKEY,
            exc,
            context={"exchange": "binance", "pair": "BTC/USDT"},
        )

    assert result is not None
    assert "hash" in result
    assert "errorId" in result
    assert "errorSecret" in result
    assert len(result["errorId"]) == 32
    assert len(result["errorSecret"]) == 64


async def test_upload_error_encrypted_at_rest(sync_client, s3_store):
    """Uploaded error data is encrypted in S3 (delegated encryption)."""
    try:
        raise ValueError("secret trading error")
    except ValueError as exc:
        result = await upload_error(sync_client, USER_PUBKEY, exc)

    salt = result["errorId"]
    raw = await s3_store.get_string(f"users/{USER_PUBKEY}/errors/{salt}")
    assert raw is not None
    assert "secret trading error" not in raw
    assert "ValueError" not in raw


async def test_upload_error_decryptable_with_credentials(sync_client):
    """Error can be decrypted using the returned errorId and errorSecret."""
    try:
        raise RuntimeError("decryption test")
    except RuntimeError as exc:
        result = await upload_error(
            sync_client,
            USER_PUBKEY,
            exc,
            context={"exchange": "binance"},
        )

    salt = result["errorId"]
    error_secret = result["errorSecret"]

    manager = SyncManager(
        client=sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=salt),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=salt),
        encryption_secret=error_secret,
        encryption_salt=salt,
        encryption_info=ENCRYPTION_INFO,
    )
    data = await manager.pull()
    assert data["message"] == "decryption test"
    assert data["type"] == "RuntimeError"
    assert data["context"]["exchange"] == "binance"


async def test_upload_error_includes_version(sync_client, monkeypatch):
    """Error payload includes the OctoBot version (verifiable after decryption)."""
    monkeypatch.setattr("octobot.constants.LONG_VERSION", "1.2.3-test")
    try:
        raise TypeError("version check")
    except TypeError as exc:
        result = await upload_error(sync_client, USER_PUBKEY, exc)

    manager = SyncManager(
        client=sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        encryption_secret=result["errorSecret"],
        encryption_salt=result["errorId"],
        encryption_info=ENCRYPTION_INFO,
    )
    data = await manager.pull()
    assert data["version"] == "1.2.3-test"


async def test_upload_error_includes_bot_id(sync_client, monkeypatch):
    """Error payload includes bot_id when COMMUNITY_BOT_ID is set."""
    monkeypatch.setattr("octobot.constants.COMMUNITY_BOT_ID", "bot-42")
    try:
        raise KeyError("bot id check")
    except KeyError as exc:
        result = await upload_error(sync_client, USER_PUBKEY, exc)

    manager = SyncManager(
        client=sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        encryption_secret=result["errorSecret"],
        encryption_salt=result["errorId"],
        encryption_info=ENCRYPTION_INFO,
    )
    data = await manager.pull()
    assert data["bot_id"] == "bot-42"
