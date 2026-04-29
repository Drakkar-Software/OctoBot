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

"""Tests for replica config helpers (is_replicable_collection, make_replica_config)."""

import pytest

from starfish_server.config.schema import (
    CollectionConfig,
    SyncConfig,
    WriteMode,
    SyncTrigger,
)

from octobot_sync.sync.collections import (
    is_replicable_collection,
    make_replica_config,
    DEFAULT_SYNC_CONFIG,
)


def _col(name: str, path: str) -> CollectionConfig:
    return CollectionConfig(
        name=name,
        storagePath=path,
        readRoles=["self"],
        writeRoles=["self"],
        encryption="identity",
        maxBodyBytes=64 * 1024,
    )


def test_is_replicable_no_template():
    col = _col("static-col", "shared/catalog")
    assert is_replicable_collection(col) is True


def test_is_replicable_with_identity():
    col = _col("per-user", "tenants/{identity}")
    assert is_replicable_collection(col) is False


def test_is_replicable_with_multiple_templates():
    col = _col("nested", "tenants/{identity}/entries/{entryId}")
    assert is_replicable_collection(col) is False


def test_make_replica_config_keeps_all_collections():
    """All collections are kept — static ones get RemoteConfig, templated ones stay as-is."""
    updated = make_replica_config(
        DEFAULT_SYNC_CONFIG, "https://primary.example.com"
    )
    assert len(updated.collections) == len(DEFAULT_SYNC_CONFIG.collections)
    # Templated collections should have no remote
    for col in updated.collections:
        if "{" in col.storage_path:
            assert col.remote is None


def test_make_replica_config_with_static_collection():
    """A static-path collection gets RemoteConfig; templated ones don't."""
    config = SyncConfig(
        version=1,
        collections=[
            _col("static-col", "shared/catalog"),
            _col("per-user", "tenants/{identity}"),
        ],
    )
    updated = make_replica_config(config, "https://primary.example.com")
    assert len(updated.collections) == 2

    static = next(c for c in updated.collections if c.name == "static-col")
    assert static.remote is not None
    assert static.remote.url == "https://primary.example.com"

    templated = next(c for c in updated.collections if c.name == "per-user")
    assert templated.remote is None


def test_make_replica_config_remote_fields():
    """Verify RemoteConfig has correct url, pullPath, pushPath, writeMode, intervalMs."""
    config = SyncConfig(
        version=1,
        collections=[_col("static-col", "shared/catalog")],
    )
    updated = make_replica_config(
        config,
        "https://primary.example.com",
        write_mode="bidirectional",
        sync_interval_ms=30_000,
    )
    remote = updated.collections[0].remote
    assert remote.url == "https://primary.example.com"
    assert remote.pull_path == "/pull/shared/catalog"
    assert remote.push_path == "/push/shared/catalog"
    assert remote.write_mode == WriteMode.BIDIRECTIONAL
    assert remote.interval_ms == 30_000
    assert SyncTrigger.ON_PULL in remote.sync_triggers
    assert SyncTrigger.SCHEDULED in remote.sync_triggers


def test_make_replica_config_pull_only_no_push_path():
    """write_mode=pull_only → pushPath is None."""
    config = SyncConfig(
        version=1,
        collections=[_col("static-col", "shared/catalog")],
    )
    updated = make_replica_config(
        config, "https://primary.example.com", write_mode="pull_only"
    )
    remote = updated.collections[0].remote
    assert remote.push_path is None
    assert remote.write_mode == WriteMode.PULL_ONLY
