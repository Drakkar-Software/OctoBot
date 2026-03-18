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

"""Integration tests — full app with mock deps, hit all manual routes."""

from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import tests.mock_chain as mock_chain_module
from tests.conftest import MemoryObjectStore


ADMIN_PUBKEY = "0xAdminPubkey"
USER_PUBKEY = "0xUserPubkey"
CHAIN_ID = "mock"

COLLECTIONS_PATH = str(Path(__file__).resolve().parent / "fixtures" / "collections.json")


@pytest.fixture
def mock_chain():
    return mock_chain_module.MockChain(CHAIN_ID)


@pytest.fixture
def app(mock_chain, monkeypatch):
    monkeypatch.setenv("PLATFORM_PUBKEY_EVM", ADMIN_PUBKEY)
    monkeypatch.setenv("ENCRYPTION_SECRET", "test-encryption-secret")
    monkeypatch.setenv("PLATFORM_ENCRYPTION_SECRET", "test-platform-secret")
    registry = chain.ChainRegistry()
    registry.register(mock_chain)
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    object_store = MemoryObjectStore()
    return sync_app.create_app(nonce, object_store, registry, collections_path=COLLECTIONS_PATH)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac




async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "ts" in data




async def test_verify_public_read(client):
    """Public GETs on products/ should pass without auth."""
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_ORIGINAL_METHOD: "GET",
            constants.HEADER_ORIGINAL_URI: "/octobot-sync-dev/products/some-product/data.json",
        },
    )
    assert resp.status_code == 200


async def test_verify_missing_headers(client):
    resp = await client.get("/verify")
    assert resp.status_code == 401




async def test_get_product_not_found(client):
    resp = await client.get("/v1/product/nonexistent")
    assert resp.status_code == 404


async def test_get_product_found(client, mock_chain):
    mock_chain.set_item("prod-1", chain.Item(id="prod-1", owner="0xOwner"))
    resp = await client.get("/v1/product/prod-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"]["id"] == "prod-1"
    assert data["product"]["owner"] == "0xOwner"




async def test_get_product_info(client, mock_chain):
    mock_chain.set_item("prod-2", chain.Item(id="prod-2", owner="0xOwner2"))
    resp = await client.get("/v1/product/prod-2/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"]["id"] == "prod-2"




async def test_verify_public_path_read(client):
    resp = await client.get(
        "/verify",
        headers={
            constants.HEADER_ORIGINAL_METHOD: "GET",
            constants.HEADER_ORIGINAL_URI: "/bucket/public/some-file.json",
        },
    )
    assert resp.status_code == 200




async def test_put_product_meta_invalid_version(client):
    resp = await client.put("/v1/product/prod-1/invalid/meta")
    assert resp.status_code == 400


async def test_put_product_meta_invalid_tags(client):
    resp = await client.put(
        "/v1/product/prod-1/v1/meta",
        data={"tags": "not-json"},
    )
    assert resp.status_code == 400


async def test_put_product_meta_profile_fields(client):
    resp = await client.put(
        "/v1/product/prod-1/v1/meta",
        data={"name": "My Product", "description": "A test product"},
    )
    assert resp.status_code == 200

    resp = await client.get("/v1/product/prod-1/info")
    profile = resp.json()["profile"]
    assert profile["name"] == "My Product"
    assert profile["description"] == "A test product"
