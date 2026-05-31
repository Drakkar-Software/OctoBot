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

"""Shared fixtures for e2e tests (require S3_ENDPOINT in environment)."""

import os
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

import octobot_sync.app as sync_app

# Well-known Hardhat test key #1 — safe to embed in tests.
USER_PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
OTHER_PRIVATE_KEY = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"

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
        for prefix in ("test/", "users/", "public/"):
            keys = await store.list_keys(prefix)
            if keys:
                await store.delete_many(keys)
    finally:
        await store.close()


@pytest.fixture
def app(s3_store):
    return sync_app.create_app(s3_store, collections_path=COLLECTIONS_PATH)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/sync") as ac:
        yield ac
