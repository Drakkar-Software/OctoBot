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
from unittest.mock import patch

import pytest
from httpx import ASGITransport

from octobot_sync.client import StarfishClient, pull_payload

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.constants as constants
from octobot.community.errors_upload.error_sharing import (
    upload_error,
    ERRORS_PULL_PATH_TEMPLATE,
    ERRORS_PUSH_PATH_TEMPLATE,
    ENCRYPTION_INFO,
)
from tests.e2e.conftest import USER_PUBKEY, COLLECTIONS_PATH

pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_ENDPOINT"),
    reason="S3_ENDPOINT not set — skipping e2e tests",
)


def _make_auth_provider(pubkey: str):
    """Auth provider that builds fake-signed headers; requires verify_evm to be patched."""
    async def auth_provider(
        *, method: str, path: str, body: str | None
    ) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        nonce = f"err-nonce-{uuid.uuid4()}"
        body_hash = auth.hash_body(body or "")
        canonical = auth.build_canonical(method, path, ts, nonce, body_hash)
        signature = f"err-sig-{ts}"
        auth_provider._last_canonical = canonical
        auth_provider._last_sig = signature

        return {
            constants.HEADER_PUBKEY: pubkey,
            constants.HEADER_SIGNATURE: signature,
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: nonce,
        }

    return auth_provider


@pytest.fixture
async def sync_client(s3_store):
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    with patch.dict(os.environ, {"ENCRYPTION_SECRET": "e2e-encryption-secret"}):
        app = sync_app.create_app(nonce, s3_store, collections_path=COLLECTIONS_PATH)

    import httpx

    transport = ASGITransport(app=app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    client = StarfishClient(
        base_url="http://test",
        auth=_make_auth_provider(USER_PUBKEY),
        client=http_client,
    )
    with patch("octobot_sync.chain.verify_evm", return_value=True):
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

    data = await pull_payload(
        sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=salt),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=salt),
        encryption_secret=error_secret,
        encryption_salt=salt,
        encryption_info=ENCRYPTION_INFO,
    )
    assert data["message"] == "decryption test"
    assert data["type"] == "RuntimeError"
    assert data["context"]["exchange"] == "binance"


async def test_upload_error_includes_version(sync_client):
    """Error payload includes the OctoBot version (verifiable after decryption)."""
    with patch("octobot.constants.LONG_VERSION", "1.2.3-test"):
        try:
            raise TypeError("version check")
        except TypeError as exc:
            result = await upload_error(sync_client, USER_PUBKEY, exc)

    data = await pull_payload(
        sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        encryption_secret=result["errorSecret"],
        encryption_salt=result["errorId"],
        encryption_info=ENCRYPTION_INFO,
    )
    assert data["version"] == "1.2.3-test"


async def test_upload_error_includes_bot_id(sync_client):
    """Error payload includes bot_id when COMMUNITY_BOT_ID is set."""
    with patch("octobot.constants.COMMUNITY_BOT_ID", "bot-42"):
        try:
            raise KeyError("bot id check")
        except KeyError as exc:
            result = await upload_error(sync_client, USER_PUBKEY, exc)

    data = await pull_payload(
        sync_client,
        pull_path=ERRORS_PULL_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        push_path=ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=USER_PUBKEY, errorId=result["errorId"]),
        encryption_secret=result["errorSecret"],
        encryption_salt=result["errorId"],
        encryption_info=ENCRYPTION_INFO,
    )
    assert data["bot_id"] == "bot-42"
