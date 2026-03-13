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

"""Tests for sync collection definitions loaded from collections.json."""

from pathlib import Path

import octobot_commons.constants as commons_constants
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collections as collections_module

_OCTOBOT_ROOT = Path(__file__).resolve().parents[3]
COLLECTIONS_PATH = str(
    _OCTOBOT_ROOT / commons_constants.USER_FOLDER / sync_constants.COLLECTIONS_FILE
)


def _load():
    return collections_module.load_sync_config(COLLECTIONS_PATH)


def test_sync_config_version():
    assert _load().version == 1


def test_sync_config_has_collections():
    assert len(_load().collections) == 25


def test_all_collections_have_names():
    config = _load()
    names = [c.name for c in config.collections]
    assert all(names)
    assert len(names) == len(set(names)), "Duplicate collection names"


def test_signals_collection():
    signals = next(c for c in _load().collections if c.name == "signals")
    assert signals.storage_path == "products/{productId}/signals/{version}"
    assert "public" in signals.read_roles
    assert "owner" in signals.write_roles
    assert signals.encryption == "none"
    assert signals.rate_limit is True


def test_bundled_user_data():
    bundled = [c for c in _load().collections if c.bundle == "user-data"]
    assert len(bundled) == 4
    names = {c.name for c in bundled}
    assert names == {"bots", "accounts", "settings", "notifications"}
    for c in bundled:
        assert c.encryption == "identity"
        assert c.storage_path == "users/{identity}"


def test_pull_only_collections():
    pull_only = [c for c in _load().collections if c.pull_only]
    assert len(pull_only) == 5
    names = {c.name for c in pull_only}
    assert "news" in names
    assert "courses" in names
    assert "exchanges" in names
    assert "cryptocurrencies" in names
    assert "cryptocurrency-detail" in names


def test_platform_encrypted_collections():
    server_encrypted = [c for c in _load().collections if c.encryption == "server"]
    assert len(server_encrypted) == 2
    names = {c.name for c in server_encrypted}
    assert names == {"platform-affiliates", "platform-referrals"}


def test_rate_limit_config():
    config = _load()
    assert config.rate_limit is not None
    assert config.rate_limit.window_ms == 60_000
    assert config.rate_limit.max_requests == 100
