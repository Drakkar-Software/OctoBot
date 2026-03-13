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

"""Tests for role resolver, enricher, and signature verifier."""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from satellite_server.router.route_builder import AuthResult

import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import octobot_sync.sync as sync
import tests.mock_chain as mock_chain_module


PUBKEY = "0xTestUser"
ADMIN_PUBKEY = "0xAdmin"
CHAIN_ID = "mock"


@pytest.fixture
def mock_chain():
    return mock_chain_module.MockChain(CHAIN_ID)


@pytest.fixture
def registry(mock_chain):
    r = chain.ChainRegistry()
    r.register(mock_chain)
    return r


@pytest.fixture
def nonce():
    return auth.NonceStore(auth.MemoryStorageAdapter())


def _make_request(method: str, path: str, body: str, headers: dict) -> MagicMock:
    """Create a mock FastAPI Request."""
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = headers
    req.url = MagicMock()
    req.url.__str__ = lambda self: f"http://localhost{path}"
    req.body = AsyncMock(return_value=body.encode("utf-8") if body else b"")
    return req


async def test_role_resolver_success(mock_chain, registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)

    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-1"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "test-sig"
    mock_chain.set_signature_valid(canonical, sig, PUBKEY, True)

    headers = {
        constants.HEADER_PUBKEY: PUBKEY,
        constants.HEADER_SIGNATURE: sig,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce_val,
        constants.HEADER_CHAIN: CHAIN_ID,
    }
    req = _make_request("GET", "/v1/test", "", headers)
    result = await resolver(req)
    assert result.identity == PUBKEY
    assert "user" in result.roles
    assert "admin" not in result.roles


async def test_role_resolver_admin(mock_chain, registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)

    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-admin"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "admin-sig"
    mock_chain.set_signature_valid(canonical, sig, ADMIN_PUBKEY, True)

    headers = {
        constants.HEADER_PUBKEY: ADMIN_PUBKEY,
        constants.HEADER_SIGNATURE: sig,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce_val,
        constants.HEADER_CHAIN: CHAIN_ID,
    }
    req = _make_request("GET", "/v1/test", "", headers)
    result = await resolver(req)
    assert "admin" in result.roles


async def test_role_resolver_missing_headers(registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)
    req = _make_request("GET", "/", "", {})
    with pytest.raises(ValueError, match="Missing authentication headers"):
        await resolver(req)


async def test_role_resolver_replay_rejected(mock_chain, registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)

    ts = str(int(time.time() * 1000))
    nonce_val = "replay-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "replay-sig"
    mock_chain.set_signature_valid(canonical, sig, PUBKEY, True)

    headers = {
        constants.HEADER_PUBKEY: PUBKEY,
        constants.HEADER_SIGNATURE: sig,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce_val,
        constants.HEADER_CHAIN: CHAIN_ID,
    }
    req1 = _make_request("GET", "/v1/test", "", headers)
    await resolver(req1)  # First succeeds

    req2 = _make_request("GET", "/v1/test", "", headers)
    with pytest.raises(ValueError, match="Replay"):
        await resolver(req2)


async def test_role_enricher_owner(mock_chain, registry):
    enricher = sync.create_role_enricher(registry)
    mock_chain.set_owner("product-123", PUBKEY)

    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "owner" in extra


async def test_role_enricher_not_owner(mock_chain, registry):
    enricher = sync.create_role_enricher(registry)
    mock_chain.set_owner("product-123", "0xSomeoneElse")

    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert extra == []


async def test_signature_verifier_uses_chain(mock_chain, registry):
    mock_chain.set_signature_valid("data", "sig", "pk", True)
    verifier = sync.create_signature_verifier(registry)
    assert await verifier("data", "sig", "pk") is True


async def test_signature_verifier_rejects_invalid(registry):
    verifier = sync.create_signature_verifier(registry)
    assert await verifier("data", "bad-sig", "pk") is False


async def test_role_resolver_expired_timestamp(mock_chain, registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)

    ts = str(int(time.time() * 1000) - 120_000)  # 2 minutes ago
    nonce_val = "expired-ts-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "expired-sig"
    mock_chain.set_signature_valid(canonical, sig, PUBKEY, True)

    headers = {
        constants.HEADER_PUBKEY: PUBKEY,
        constants.HEADER_SIGNATURE: sig,
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: nonce_val,
        constants.HEADER_CHAIN: CHAIN_ID,
    }
    req = _make_request("GET", "/v1/test", "", headers)
    with pytest.raises(ValueError, match="Timestamp out of window"):
        await resolver(req)


async def test_role_resolver_unknown_chain(registry, nonce):
    resolver = sync.create_role_resolver(registry, nonce, ADMIN_PUBKEY)

    ts = str(int(time.time() * 1000))
    headers = {
        constants.HEADER_PUBKEY: PUBKEY,
        constants.HEADER_SIGNATURE: "sig",
        constants.HEADER_TIMESTAMP: ts,
        constants.HEADER_NONCE: "nonce-unknown",
        constants.HEADER_CHAIN: "unknown-chain",
    }
    req = _make_request("GET", "/v1/test", "", headers)
    with pytest.raises(ValueError, match="Unknown chain"):
        await resolver(req)


async def test_role_enricher_no_product_id(mock_chain, registry):
    enricher = sync.create_role_enricher(registry)
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {})
    assert extra == []


async def test_find_item(mock_chain, registry):
    mock_chain.set_item("item-1", chain.Item(id="item-1", owner="0xOwner"))
    result = await sync.find_item(registry, "item-1")
    assert result is not None
    assert result.id == "item-1"


async def test_find_item_not_found(registry):
    result = await sync.find_item(registry, "nonexistent")
    assert result is None
