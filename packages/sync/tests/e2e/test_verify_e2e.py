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

"""E2E tests — /verify endpoint: auth flow, path authorization, edge cases."""

import os
import time

import pytest

import octobot_sync.constants as constants
from tests.e2e.conftest import (
    ADMIN_PUBKEY,
    USER_PUBKEY,
    OTHER_PUBKEY,
    CHAIN_ID,
    make_verify_headers,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_ENDPOINT"),
    reason="S3_ENDPOINT not set — skipping e2e tests",
)


async def test_public_read_products_no_auth_needed(client):
    """GET on products/ passes without any auth headers."""
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_ORIGINAL_METHOD: "GET",
            constants.HEADER_ORIGINAL_URI: "/bucket/products/prod-1/signals.json",
        },
    )
    assert resp.status_code == 200


async def test_public_read_public_path_no_auth_needed(client):
    """GET on public/ passes without any auth headers."""
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_ORIGINAL_METHOD: "GET",
            constants.HEADER_ORIGINAL_URI: "/bucket/public/news/2026-03.json",
        },
    )
    assert resp.status_code == 200


async def test_no_headers_at_all_rejected(client):
    resp = await client.get("/verify")
    assert resp.status_code == 401


async def test_missing_one_auth_header_rejected(client):
    """Providing only some auth headers is still rejected."""
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_TIMESTAMP: str(int(time.time() * 1000)),
        },
    )
    assert resp.status_code == 401


async def test_admin_can_write_products(client, mock_chain):
    """Admin pubkey is authorized to PUT on products/."""
    headers = make_verify_headers(
        mock_chain, ADMIN_PUBKEY, "PUT", "/bucket/products/prod-1/data.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 200


async def test_user_cannot_write_products(client, mock_chain):
    """Regular user is not authorized to PUT on products/."""
    headers = make_verify_headers(
        mock_chain, USER_PUBKEY, "PUT", "/bucket/products/prod-1/data.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 401


async def test_admin_can_write_public(client, mock_chain):
    """Admin pubkey can PUT on public/ paths."""
    headers = make_verify_headers(
        mock_chain, ADMIN_PUBKEY, "PUT", "/bucket/public/highlights.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 200


async def test_user_cannot_write_public(client, mock_chain):
    """Regular user cannot PUT on public/ paths."""
    headers = make_verify_headers(
        mock_chain, USER_PUBKEY, "PUT", "/bucket/public/highlights.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 401


async def test_user_can_access_own_path(client, mock_chain):
    """User can read and write their own users/{pubkey}/ path."""
    for method in ("GET", "PUT"):
        headers = make_verify_headers(
            mock_chain, USER_PUBKEY, method, f"/bucket/users/{USER_PUBKEY}/data.json"
        )
        resp = await client.get("/verify", headers=headers)
        assert resp.status_code == 200, f"{method} own path should be allowed"


async def test_user_cannot_access_other_user_path(client, mock_chain):
    """User cannot read or write another user's path."""
    for method in ("GET", "PUT"):
        headers = make_verify_headers(
            mock_chain, USER_PUBKEY, method, f"/bucket/users/{OTHER_PUBKEY}/data.json"
        )
        resp = await client.get("/verify", headers=headers)
        assert resp.status_code == 401, f"{method} other user's path should be denied"


async def test_admin_can_access_any_user_path(client, mock_chain):
    """Admin can read and write any user's path."""
    for method in ("GET", "PUT"):
        headers = make_verify_headers(
            mock_chain, ADMIN_PUBKEY, method, f"/bucket/users/{USER_PUBKEY}/data.json"
        )
        resp = await client.get("/verify", headers=headers)
        assert resp.status_code == 200, f"Admin {method} any user path should work"


async def test_only_admin_can_access_platform(client, mock_chain):
    """Only admin can read or write platform/ paths."""
    headers_admin = make_verify_headers(
        mock_chain, ADMIN_PUBKEY, "GET", "/bucket/platform/config.json"
    )
    resp = await client.get("/verify", headers=headers_admin)
    assert resp.status_code == 200

    headers_user = make_verify_headers(
        mock_chain, USER_PUBKEY, "GET", "/bucket/platform/config.json"
    )
    resp = await client.get("/verify", headers=headers_user)
    assert resp.status_code == 401


async def test_unknown_path_prefix_rejected(client, mock_chain):
    """Paths not under products/public/users/platform are rejected."""
    headers = make_verify_headers(
        mock_chain, ADMIN_PUBKEY, "GET", "/bucket/unknown/file.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 401


async def test_expired_timestamp_rejected(client):
    """Timestamp older than TIMESTAMP_WINDOW_MS is rejected."""
    old_ts = str(int(time.time() * 1000) - 120_000)
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_SIGNATURE: "sig",
            constants.HEADER_TIMESTAMP: old_ts,
            constants.HEADER_NONCE: "e2e-expired-nonce",
            constants.HEADER_CHAIN: CHAIN_ID,
            constants.HEADER_ORIGINAL_METHOD: "PUT",
            constants.HEADER_ORIGINAL_URI: "/bucket/users/x/data.json",
        },
    )
    assert resp.status_code == 401


async def test_non_numeric_timestamp_rejected(client):
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_SIGNATURE: "sig",
            constants.HEADER_TIMESTAMP: "not-a-number",
            constants.HEADER_NONCE: "nonce",
            constants.HEADER_CHAIN: CHAIN_ID,
        },
    )
    assert resp.status_code == 401


async def test_invalid_signature_rejected(client):
    """Valid headers but wrong signature is rejected."""
    ts = str(int(time.time() * 1000))
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_SIGNATURE: "wrong-signature",
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: "e2e-badsig-nonce",
            constants.HEADER_CHAIN: CHAIN_ID,
            constants.HEADER_ORIGINAL_METHOD: "PUT",
            constants.HEADER_ORIGINAL_URI: f"/bucket/users/{USER_PUBKEY}/data.json",
        },
    )
    assert resp.status_code == 401


async def test_nonce_replay_rejected(client, mock_chain):
    """Same nonce+pubkey used twice is rejected on the second request."""
    headers = make_verify_headers(
        mock_chain, ADMIN_PUBKEY, "PUT", "/bucket/platform/config.json"
    )
    resp1 = await client.get("/verify", headers=headers)
    assert resp1.status_code == 200

    resp2 = await client.get("/verify", headers=headers)
    assert resp2.status_code == 401


async def test_unknown_chain_rejected(client):
    """Request referencing a non-registered chain ID is rejected."""
    ts = str(int(time.time() * 1000))
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_SIGNATURE: "sig",
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: "e2e-unknown-chain",
            constants.HEADER_CHAIN: "nonexistent-chain",
            constants.HEADER_ORIGINAL_METHOD: "PUT",
            constants.HEADER_ORIGINAL_URI: f"/bucket/users/{USER_PUBKEY}/data.json",
        },
    )
    assert resp.status_code == 401


async def test_oversized_pubkey_rejected(client):
    """Pubkey exceeding MAX_PUBKEY_LENGTH is rejected."""
    ts = str(int(time.time() * 1000))
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: "x" * (constants.MAX_PUBKEY_LENGTH + 1),
            constants.HEADER_SIGNATURE: "sig",
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: "e2e-oversized",
            constants.HEADER_CHAIN: CHAIN_ID,
        },
    )
    assert resp.status_code == 401


async def test_oversized_signature_rejected(client):
    """Signature exceeding MAX_SIGNATURE_LENGTH is rejected."""
    ts = str(int(time.time() * 1000))
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_PUBKEY: USER_PUBKEY,
            constants.HEADER_SIGNATURE: "s" * (constants.MAX_SIGNATURE_LENGTH + 1),
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: "e2e-oversized-sig",
            constants.HEADER_CHAIN: CHAIN_ID,
        },
    )
    assert resp.status_code == 401


async def test_head_method_is_read(client, mock_chain):
    """HEAD requests are treated as reads (same as GET)."""
    headers = make_verify_headers(
        mock_chain, USER_PUBKEY, "HEAD", "/bucket/products/prod-1/data.json"
    )
    resp = await client.get("/verify", headers=headers)
    assert resp.status_code == 200


