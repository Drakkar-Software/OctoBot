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
        assert c.encryption == "identity"
        assert c.storage_path == "users/{identity}"


def test_pull_only_collections():
    pull_only = [c for c in _load().collections if c.pull_only]
    assert len(pull_only) == 1
    assert pull_only[0].name == "epsilon-catalog"


def test_server_encrypted_collections():
    server_encrypted = [c for c in _load().collections if c.encryption == "server"]
    assert len(server_encrypted) == 1
    assert server_encrypted[0].name == "zeta-internal"


def test_rate_limit_config():
    config = _load()
    assert config.rate_limit is not None
    assert config.rate_limit.window_ms == 60_000
    assert config.rate_limit.max_requests == 100


def test_fallback_to_default_config():
    """When collections file is missing, DEFAULT_SYNC_CONFIG is returned."""
    config = collections_module.load_sync_config("/nonexistent/path.json")
    assert config.version == 1
    assert len(config.collections) == 3
    names = {c.name for c in config.collections}
    assert names == {"bots", "accounts", "errors"}
