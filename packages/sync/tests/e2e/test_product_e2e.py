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

"""E2E tests — product lifecycle with real S3 storage."""

import json
import os

import pytest

import octobot_sync.chain as chain

pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_ENDPOINT"),
    reason="S3_ENDPOINT not set — skipping e2e tests",
)


async def test_full_product_lifecycle(client, mock_chain, s3_store):
    """Create product → upload meta → read info → update meta → read again → verify S3 keys."""
    pid = "e2e-lifecycle"
    mock_chain.set_item(pid, chain.Item(id=pid, owner="0xLifecycleOwner"))

    resp = await client.put(
        f"/v1/product/{pid}/v1/meta",
        data={
            "name": "Lifecycle Bot",
            "description": "Initial description",
            "website": "https://octobot.cloud",
            "tags": json.dumps(["defi", "arbitrage"]),
        },
    )
    assert resp.status_code == 200

    resp = await client.get(f"/v1/product/{pid}/info")
    info = resp.json()
    assert info["product"]["owner"] == "0xLifecycleOwner"
    assert info["profile"]["name"] == "Lifecycle Bot"
    assert info["profile"]["tags"] == ["defi", "arbitrage"]

    resp = await client.put(
        f"/v1/product/{pid}/v1/meta",
        data={
            "name": "Lifecycle Bot v2",
            "description": "Updated description",
            "twitter": "@lifecycle",
        },
    )
    assert resp.status_code == 200

    resp = await client.get(f"/v1/product/{pid}/info")
    profile = resp.json()["profile"]
    assert profile["name"] == "Lifecycle Bot v2"
    assert profile["description"] == "Updated description"
    assert profile["website"] == "https://octobot.cloud"
    assert profile["twitter"] == "@lifecycle"
    assert profile["tags"] == ["defi", "arbitrage"]

    raw = await s3_store.get_string(f"products/{pid}/profile.json")
    assert raw is not None
    stored = json.loads(raw)
    assert stored["name"] == "Lifecycle Bot v2"


async def test_multiple_products_isolated(client, mock_chain):
    """Two products with separate profiles don't interfere with each other."""
    for suffix, owner, name in [("alpha", "0xA", "Alpha"), ("beta", "0xB", "Beta")]:
        pid = f"e2e-iso-{suffix}"
        mock_chain.set_item(pid, chain.Item(id=pid, owner=owner))
        await client.put(f"/v1/product/{pid}/v1/meta", data={"name": name})

    resp_a = await client.get("/v1/product/e2e-iso-alpha/info")
    resp_b = await client.get("/v1/product/e2e-iso-beta/info")
    assert resp_a.json()["profile"]["name"] == "Alpha"
    assert resp_a.json()["product"]["owner"] == "0xA"
    assert resp_b.json()["profile"]["name"] == "Beta"
    assert resp_b.json()["product"]["owner"] == "0xB"


async def test_version_descriptions_across_versions(client, s3_store):
    """Version descriptions are stored separately per version."""
    pid = "e2e-versions"

    await client.put(
        f"/v1/product/{pid}/v1/meta",
        data={"version_description": "First release"},
    )
    await client.put(
        f"/v1/product/{pid}/v2/meta",
        data={"version_description": "Major update"},
    )

    v1_raw = await s3_store.get_string(f"products/{pid}/v1/document.json")
    v2_raw = await s3_store.get_string(f"products/{pid}/v2/document.json")
    assert json.loads(v1_raw)["description"] == "First release"
    assert json.loads(v2_raw)["description"] == "Major update"


async def test_product_endpoint_returns_404_without_chain_item(client):
    """GET /product/{id} returns 404 when the product doesn't exist on chain."""
    resp = await client.get("/v1/product/e2e-ghost")
    assert resp.status_code == 404
    assert resp.json()["error"] == "Product not found"


async def test_product_info_returns_null_product_without_chain_item(client):
    """GET /product/{id}/info returns null product when not on chain, empty profile."""
    resp = await client.get("/v1/product/e2e-ghost/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"] is None
    assert data["profile"] == {}


async def test_product_info_with_profile_but_no_chain_item(client, s3_store):
    """Profile can exist in S3 even if product isn't on chain (e.g. delisted)."""
    pid = "e2e-delisted"
    await s3_store.put(
        f"products/{pid}/profile.json",
        json.dumps({"name": "Delisted Bot"}),
        content_type="application/json",
    )

    resp = await client.get(f"/v1/product/{pid}/info")
    data = resp.json()
    assert data["product"] is None
    assert data["profile"]["name"] == "Delisted Bot"


async def test_meta_invalid_version_rejected(client):
    resp = await client.put("/v1/product/e2e-bad/invalid/meta")
    assert resp.status_code == 400
    assert resp.json()["error"] == "Invalid version"


async def test_meta_invalid_tags_json_rejected(client):
    resp = await client.put(
        "/v1/product/e2e-bad/v1/meta",
        data={"tags": "not-valid-json["},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Invalid tags JSON"


async def test_meta_empty_form_is_noop(client, s3_store):
    """Submitting meta with no fields doesn't create a profile document."""
    pid = "e2e-empty-meta"
    resp = await client.put(f"/v1/product/{pid}/v1/meta", data={})
    assert resp.status_code == 200

    raw = await s3_store.get_string(f"products/{pid}/profile.json")
    assert raw is None


async def test_product_endpoint_no_profile_returns_empty(client, mock_chain):
    """GET /product/{id} works even when no profile has been uploaded."""
    pid = "e2e-no-profile"
    mock_chain.set_item(pid, chain.Item(id=pid, owner="0xNoProfile"))

    resp = await client.get(f"/v1/product/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"]["id"] == pid
    assert data["profile"] == {}
