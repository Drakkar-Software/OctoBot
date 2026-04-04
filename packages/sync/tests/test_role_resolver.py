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

import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from starfish_server.router.route_builder import AuthResult

import octobot_sync.auth as auth
import octobot_sync.constants as constants
import octobot_sync.sync as sync
from tests.conftest import MockVerifyFn, MemoryObjectStore


PUBKEY = "0xTestUser"
ADMIN_PUBKEY = "0xAdmin"
CHAIN_ID = "mock"
SUPPORTED_CHAINS = {CHAIN_ID}


@pytest.fixture
def mock_verify():
    return MockVerifyFn()


@pytest.fixture
def nonce():
    return auth.NonceStore(auth.MemoryStorageAdapter())


@pytest.fixture
def store():
    return MemoryObjectStore()


def _make_request(method: str, path: str, body: str, headers: dict) -> MagicMock:
    """Create a mock FastAPI Request."""
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = headers
    req.url = MagicMock()
    req.url.__str__ = lambda self: f"http://localhost{path}"
    req.body = AsyncMock(return_value=body.encode("utf-8") if body else b"")
    return req


# --- Role resolver tests ---

async def test_role_resolver_success(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)

    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-1"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "test-sig"
    mock_verify.set_valid(canonical, sig, PUBKEY)

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


async def test_role_resolver_admin(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)

    ts = str(int(time.time() * 1000))
    nonce_val = "test-nonce-admin"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "admin-sig"
    mock_verify.set_valid(canonical, sig, ADMIN_PUBKEY)

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


async def test_role_resolver_missing_headers(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)
    req = _make_request("GET", "/", "", {})
    with pytest.raises(ValueError, match="Missing authentication headers"):
        await resolver(req)


async def test_role_resolver_replay_rejected(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)

    ts = str(int(time.time() * 1000))
    nonce_val = "replay-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "replay-sig"
    mock_verify.set_valid(canonical, sig, PUBKEY)

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


async def test_role_resolver_expired_timestamp(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)

    ts = str(int(time.time() * 1000) - 120_000)  # 2 minutes ago
    nonce_val = "expired-ts-nonce"
    body_hash = auth.hash_body("")
    canonical = auth.build_canonical("GET", "/v1/test", ts, nonce_val, body_hash)
    sig = "expired-sig"
    mock_verify.set_valid(canonical, sig, PUBKEY)

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


async def test_role_resolver_unknown_chain(mock_verify, nonce):
    resolver = sync.create_role_resolver(mock_verify, nonce, ADMIN_PUBKEY, SUPPORTED_CHAINS)

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


# --- Role enricher tests ---

async def test_role_enricher_owner(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": PUBKEY, "members": []}),
    )
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "owner" in extra
    assert "member" in extra


async def test_role_enricher_member(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": "0xSomeoneElse", "members": [PUBKEY]}),
    )
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "member" in extra
    assert "owner" not in extra


async def test_role_enricher_member_via_entitlements(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": "0xSomeoneElse", "members": []}),
    )
    await store.put(
        f"users/{PUBKEY.lower()}/entitlements",
        json.dumps({"products": ["product-123"]}),
    )
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "member" in extra
    assert "owner" not in extra


async def test_role_enricher_no_access(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": "0xSomeoneElse", "members": []}),
    )
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert extra == []


async def test_role_enricher_no_product_id(store):
    enricher = sync.create_role_enricher(store)
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {})
    assert extra == []


async def test_role_enricher_missing_members_doc(store):
    enricher = sync.create_role_enricher(store)
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert extra == []


async def test_role_enricher_malformed_members_doc(store):
    enricher = sync.create_role_enricher(store)
    await store.put("products/product-123/members", "not-json{{{")
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert extra == []


async def test_role_enricher_case_insensitive(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": "0xABCDEF", "members": []}),
    )
    extra = await enricher(AuthResult(identity="0xabcdef", roles=["user"]), {"productId": "product-123"})
    assert "owner" in extra


async def test_role_enricher_entitlements_only_no_members_doc(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        f"users/{PUBKEY.lower()}/entitlements",
        json.dumps({"products": ["product-456"]}),
    )
    extra = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-456"})
    assert extra == ["member"]


async def test_role_enricher_entitlements_case_insensitive_identity(store):
    enricher = sync.create_role_enricher(store)
    await store.put(
        "users/0xabcdef/entitlements",
        json.dumps({"products": ["product-789"]}),
    )
    extra = await enricher(AuthResult(identity="0xABCDEF", roles=["user"]), {"productId": "product-789"})
    assert extra == ["member"]


async def test_role_enricher_cache_hit(store):
    enricher = sync.create_role_enricher(store, cache_ttl_s=60.0)
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": PUBKEY, "members": []}),
    )
    extra1 = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "owner" in extra1

    # Update the store — cache should still return old value
    await store.put(
        "products/product-123/members",
        json.dumps({"owner": "0xSomeoneElse", "members": []}),
    )
    extra2 = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-123"})
    assert "owner" in extra2  # Still cached


async def test_role_enricher_missing_doc_not_cached(store):
    enricher = sync.create_role_enricher(store, cache_ttl_s=60.0)

    # First call: doc missing → no roles
    extra1 = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-new"})
    assert extra1 == []

    # Write the doc — should be picked up immediately (None was not cached)
    await store.put(
        "products/product-new/members",
        json.dumps({"owner": PUBKEY, "members": []}),
    )
    extra2 = await enricher(AuthResult(identity=PUBKEY, roles=["user"]), {"productId": "product-new"})
    assert "owner" in extra2


# --- Signature verifier tests ---

async def test_signature_verifier_uses_verify_fn(mock_verify):
    mock_verify.set_valid("data", "sig", "pk")
    verifier = sync.create_signature_verifier(mock_verify)
    assert await verifier("data", "sig", "pk") is True


async def test_signature_verifier_rejects_invalid(mock_verify):
    verifier = sync.create_signature_verifier(mock_verify)
    assert await verifier("data", "bad-sig", "pk") is False
