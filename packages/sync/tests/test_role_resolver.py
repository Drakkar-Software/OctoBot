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

"""Tests for the role resolver."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

import octobot_sync.auth as auth
import octobot_sync.constants as constants
import octobot_sync.sync as sync


PUBKEY = "0xTestUser"


@pytest.fixture
def nonce():
    return auth.NonceStore(auth.MemoryStorageAdapter())


def _make_request(method: str, path: str, body: str, headers: dict) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = headers
    req.scope = {"path": path}
    req.body = AsyncMock(return_value=body.encode("utf-8") if body else b"")
    return req


def _make_headers(pubkey: str, canonical: str, sig: str, ts: str, nonce_val: str) -> dict:
    return {
        constants.HEADER_PUBKEY: pubkey,
        constants.HEADER_SIGNATURE: sig,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce_val,
    }


async def test_role_resolver_success(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-1"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce)
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "sig", ts, nonce_val))
        result = await resolver(req)

    assert result.identity == PUBKEY
    assert result.roles == ["user"]


async def test_role_resolver_missing_headers(nonce):
    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce)
        req = _make_request("GET", "/", "", {})
        with pytest.raises(ValueError, match="Missing authentication headers"):
            await resolver(req)


async def test_role_resolver_invalid_signature(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-invalid"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    with patch("octobot_sync.chain.verify_evm", return_value=False):
        resolver = sync.create_role_resolver(nonce)
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "bad-sig", ts, nonce_val))
        with pytest.raises(ValueError, match="Invalid signature"):
            await resolver(req)


async def test_role_resolver_replay_rejected(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "replay-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    headers = _make_headers(PUBKEY, canonical, "sig", ts, nonce_val)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce)
        req1 = _make_request("GET", "/v1/test", "", headers)
        await resolver(req1)

        req2 = _make_request("GET", "/v1/test", "", headers)
        with pytest.raises(ValueError, match="Replay"):
            await resolver(req2)


async def test_role_resolver_expired_timestamp(nonce):
    ts = str(int(time.time() * 1000) - 120_000)  # 2 minutes ago
    nonce_val = "expired-ts-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    headers = _make_headers(PUBKEY, canonical, "sig", ts, nonce_val)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce)
        req = _make_request("GET", "/v1/test", "", headers)
        with pytest.raises(ValueError, match="Timestamp out of window"):
            await resolver(req)


async def test_role_resolver_allowlist_permits_listed_wallet(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "allowlist-permit-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce, is_allowed=lambda addr: addr == PUBKEY.lower())
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "sig", ts, nonce_val))
        result = await resolver(req)

    assert result.identity == PUBKEY
    assert result.roles == ["user"]


async def test_role_resolver_allowlist_denies_unlisted_wallet(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "allowlist-deny-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce, is_allowed=lambda addr: False)
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "sig", ts, nonce_val))
        result = await resolver(req)

    assert result.identity == PUBKEY
    assert result.roles == []


async def test_role_resolver_allowlist_none_allows_all(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "no-allowlist-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce, is_allowed=None)
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "sig", ts, nonce_val))
        result = await resolver(req)

    assert result.roles == ["user"]


async def test_role_resolver_allowlist_address_normalized_lowercase(nonce):
    mixed_case_pubkey = "0xAbCdEf1234"
    ts = str(int(time.time() * 1000))
    nonce_val = "lowercase-norm-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    seen = []

    def capture_address(addr: str) -> bool:
        seen.append(addr)
        return True

    with patch("octobot_sync.chain.verify_evm", return_value=True):
        resolver = sync.create_role_resolver(nonce, is_allowed=capture_address)
        req = _make_request(
            "GET", "/v1/test", "", _make_headers(mixed_case_pubkey, canonical, "sig", ts, nonce_val)
        )
        await resolver(req)

    assert seen == [mixed_case_pubkey.lower()]


async def test_role_resolver_allowlist_not_called_on_bad_signature(nonce):
    ts = str(int(time.time() * 1000))
    nonce_val = "allowlist-bad-sig-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)

    called = []

    with patch("octobot_sync.chain.verify_evm", return_value=False):
        resolver = sync.create_role_resolver(nonce, is_allowed=lambda addr: called.append(addr) or True)
        req = _make_request("GET", "/v1/test", "", _make_headers(PUBKEY, canonical, "bad-sig", ts, nonce_val))
        with pytest.raises(ValueError, match="Invalid signature"):
            await resolver(req)

    assert called == []


