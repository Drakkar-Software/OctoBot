#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

"""End-to-end integration of the real cap-cert composition.

Drives octobot_sync.app.create_app (-> _build_role_resolver ->
create_cap_cert_role_resolver, and the SignedPathMiddleware) with a real
WalletCapProvider client, mounted under /sync exactly as the node mounts it.
This is the one test that exercises cap-cert request signing, the namespace +
mount path normalization, large (>64KB) document bodies, and an append-only
collection — together, against the actual app rather than an ad-hoc router.
"""

import httpx
import pytest
from fastapi import FastAPI

from starfish_sdk import StarfishClient, SyncManager
from starfish_server.config.schema import (
    SyncConfig,
    CollectionConfig,
    NamespaceConfig,
    AppendOnlyConfig,
)
from starfish_server.constants import ROLE_ROOT_DEVICE

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.constants as constants


class MemoryObjectStore:
    """Minimal in-memory AbstractObjectStore (every method takes *, context=None)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get_string(self, key, *, context=None):
        return self._store.get(key)

    async def put(self, key, body, *, content_type=None, cache_control=None, context=None):
        self._store[key] = body

    async def list_keys(self, prefix, *, start_after=None, limit=None, context=None):
        keys = sorted(k for k in self._store if k.startswith(prefix))
        if start_after:
            keys = [k for k in keys if k > start_after]
        return keys[:limit] if limit else keys

    async def delete(self, key, *, context=None):
        self._store.pop(key, None)

    async def delete_many(self, keys, *, context=None):
        for k in keys:
            self._store.pop(k, None)


# Well-known test key (Anvil account #1).
_PRIV = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

_CONFIG = SyncConfig(
    version=1,
    collections=[],
    namespaces={
        constants.SYNC_NAMESPACE: NamespaceConfig(
            collections=[
                CollectionConfig(
                    name="test-doc",
                    storagePath="users/{identity}/testdoc",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="none",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                # Product-scoped append-only log (mirrors the temporary
                # product-signals collection): no {identity} segment, authorized
                # by the node's self-signed root device cap (device:root).
                CollectionConfig(
                    name="product-signals",
                    storagePath="products/{product_id}/{version}/signals",
                    readRoles=[ROLE_ROOT_DEVICE],
                    writeRoles=[ROLE_ROOT_DEVICE],
                    encryption="none",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                    appendOnly=AppendOnlyConfig(
                        type="by_timestamp", requireAuthorSignature=False
                    ),
                ),
            ]
        )
    },
)


def _make_client():
    cap_provider = auth.WalletCapProvider(_PRIV)
    inner = sync_app.create_app(MemoryObjectStore(), sync_config=_CONFIG)
    root = FastAPI()
    root.mount("/sync", inner)  # mount exactly as node_api does
    http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=root), base_url="http://test/sync"
    )
    client = StarfishClient(
        base_url="http://test/sync",
        cap_provider=cap_provider,
        namespace=constants.SYNC_NAMESPACE,
        client=http_client,
    )
    return client, http_client, cap_provider.user_id


@pytest.mark.asyncio
async def test_cap_signed_push_pull_roundtrip():
    client, http_client, user_id = _make_client()
    try:
        sync = SyncManager(
            client, f"/pull/users/{user_id}/testdoc", f"/push/users/{user_id}/testdoc"
        )
        await sync.push({"hello": "world"})
        result = await sync.pull()
        assert result.data == {"hello": "world"}
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_cap_signed_large_body_not_413():
    # Pre-auth body ceiling defaults to 64KB; a private document is allowed up to
    # MAX_BODY_SIZE_PRIVATE. Push a ~512KB payload and confirm it is accepted and
    # round-trips (guards against the 64KB regression).
    client, http_client, user_id = _make_client()
    try:
        big = {"blob": "x" * (512 * 1024)}
        sync = SyncManager(
            client, f"/pull/users/{user_id}/testdoc", f"/push/users/{user_id}/testdoc"
        )
        await sync.push(big)
        result = await sync.pull()
        assert result.data == big
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_cap_signed_product_append_only_collection():
    # Product-scoped append-only path (no {identity}) authorized via device:root.
    client, http_client, _user_id = _make_client()
    try:
        path = "products/prod-123/v1/signals"
        await client.append(f"/push/{path}", {"n": 1})
        await client.append(f"/push/{path}", {"n": 2})
        items = await client.pull(f"/pull/{path}", append_field="items", full=True)
        payloads = [el["data"] if isinstance(el, dict) and "data" in el else el for el in items]
        assert {"n": 1} in payloads and {"n": 2} in payloads
    finally:
        await http_client.aclose()
