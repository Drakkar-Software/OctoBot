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

"""Tests for sync collection loading from a sample collections.json."""

from pathlib import Path

import octobot_sync.sync.collections as collections_module

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
COLLECTIONS_PATH = str(FIXTURES_DIR / "collections.json")


def _load():
    return collections_module.load_sync_config(COLLECTIONS_PATH)


def test_sync_config_version():
    assert _load().version == 1


def test_sync_config_has_collections():
    assert len(_load().collections) == 10


def test_all_collections_have_names():
    config = _load()
    names = [c.name for c in config.collections]
    assert all(names)
    assert len(names) == len(set(names)), "Duplicate collection names"


def test_rate_limited_collection():
    col = next(c for c in _load().collections if c.name == "delta-feed")
    assert col.storage_path == "items/{itemId}/feed/{version}"
    assert "member" in col.read_roles
    assert "owner" in col.write_roles
    assert col.encryption == "none"
    assert col.rate_limit


def test_bundled_collections():
    bundled = [c for c in _load().collections if c.bundle == "personal"]
    assert len(bundled) == 2
    names = {c.name for c in bundled}
    assert names == {"alpha-docs", "beta-prefs"}
    for c in bundled:
        assert c.encryption == "delegated"
        assert c.storage_path == "users/{identity}"


def test_pull_only_collections():
    pull_only = [c for c in _load().collections if c.pull_only]
    assert len(pull_only) == 1
    assert pull_only[0].name == "epsilon-catalog"


def test_server_encrypted_collections():
    # In v3, zeta-internal uses "delegated" encryption (v2 "server" is removed)
    zeta = next(c for c in _load().collections if c.name == "zeta-internal")
    assert zeta.encryption == "delegated"


def test_rate_limit_config():
    config = _load()
    assert config.rate_limit is not None
    assert config.rate_limit.window_ms == 60_000
    assert config.rate_limit.max_requests == 100


def test_fallback_to_default_config():
    """When collections file is missing, DEFAULT_SYNC_CONFIG is returned."""
    config = collections_module.load_sync_config("/nonexistent/path.json")
    assert config.version == 1
    assert config.namespaces is not None
    ns_collections = config.namespaces["octobot"].collections
    # 8 standard user collections + 1 temporary product-scoped append-only log.
    assert len(ns_collections) == 10
    by_name = {c.name: c for c in ns_collections}
    assert set(by_name) == {
        "user-data",
        "user-accounts",
        "user-accounts-auth",
        "user-accounts-trading",
        "user-accounts-history",
        "user-settings",
        "user-strategies",
        "user-actions",
        "debug",
        "product-signals",
    }
    assert by_name["user-data"].storage_path == "users/{identity}/data"
    assert by_name["user-accounts"].storage_path == "users/{identity}/accounts"
    assert by_name["user-accounts-auth"].storage_path == "users/{identity}/accounts/auth"
    assert by_name["user-accounts-trading"].storage_path == "users/{identity}/accounts/{account_id}/trading"
    assert by_name["user-accounts-history"].storage_path == "users/{identity}/accounts/{account_id}/history"
    assert by_name["user-settings"].storage_path == "users/{identity}/settings"
    assert by_name["user-strategies"].storage_path == "users/{identity}/strategies"
    assert by_name["user-actions"].storage_path == "users/{identity}/actions"
    assert by_name["debug"].storage_path == "users/{identity}/debug"
    # The 8 standard user collections are "self"-scoped and "delegated"; the
    # temporary product-signals log is a product-scoped (device:root) plaintext
    # append-only by_timestamp collection.
    for name, col in by_name.items():
        if name == "product-signals":
            continue
        assert col.read_roles == ["self"]
        assert col.write_roles == ["self"]
        assert col.encryption == "delegated"
    signals = by_name["product-signals"]
    assert signals.storage_path == "products/{product_id}/{version}/signals"
    assert signals.read_roles == ["device:root"]
    assert signals.write_roles == ["device:root"]
    assert signals.encryption == "none"
    assert signals.append_only is not None
    assert signals.append_only.type == "by_timestamp"
    assert signals.append_only.require_author_signature is False
    actions = by_name["user-actions"]
    assert actions.append_only is not None
    assert actions.append_only.type == "by_timestamp"
    assert actions.append_only.persist is False
    assert actions.append_only.require_author_signature is False
