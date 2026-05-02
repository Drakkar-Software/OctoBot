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

"""Tests for server.py helper functions."""

import os
from unittest.mock import MagicMock, patch

import pytest

import octobot_commons.constants as commons_constants
import octobot_sync.server as server


def test_require_env_present():
    with patch.dict(os.environ, {"TEST_SYNC_VAR": "hello"}):
        assert server._require_env("TEST_SYNC_VAR") == "hello"


def test_require_env_missing():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TEST_SYNC_VAR", None)
        with pytest.raises(RuntimeError, match="TEST_SYNC_VAR"):
            server._require_env("TEST_SYNC_VAR")


def _make_config(initial: dict | None = None) -> MagicMock:
    config = MagicMock()
    config.config = initial if initial is not None else {}
    config.save = MagicMock()
    return config


def test_get_or_generate_encryption_secret_uses_env_var():
    with patch.dict(os.environ, {"ENCRYPTION_SECRET": "from-env"}):
        config = _make_config()

        assert server.get_or_generate_encryption_secret(config) == "from-env"
        config.save.assert_not_called()
        assert commons_constants.CONFIG_SYNC not in config.config


def test_get_or_generate_encryption_secret_returns_existing_config_secret():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ENCRYPTION_SECRET", None)
        config = _make_config({
            commons_constants.CONFIG_SYNC: {
                commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET: "from-config"
            }
        })

        assert server.get_or_generate_encryption_secret(config) == "from-config"
        config.save.assert_not_called()


def test_get_or_generate_encryption_secret_generates_and_saves():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ENCRYPTION_SECRET", None)
        config = _make_config()

        secret = server.get_or_generate_encryption_secret(config)

        assert isinstance(secret, str)
        assert len(secret) == 64  # secrets.token_hex(32) → 64 hex chars
        assert all(c in "0123456789abcdef" for c in secret)
        assert (
            config.config[commons_constants.CONFIG_SYNC][commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET]
            == secret
        )
        config.save.assert_called_once()


def test_get_or_generate_encryption_secret_preserves_existing_sync_section():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ENCRYPTION_SECRET", None)
        config = _make_config({commons_constants.CONFIG_SYNC: {"some_other_key": "keep_me"}})

        secret = server.get_or_generate_encryption_secret(config)

        assert config.config[commons_constants.CONFIG_SYNC]["some_other_key"] == "keep_me"
        assert (
            config.config[commons_constants.CONFIG_SYNC][commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET]
            == secret
        )
        config.save.assert_called_once()


def test_get_or_generate_encryption_secret_env_var_overrides_stored():
    with patch.dict(os.environ, {"ENCRYPTION_SECRET": "env-wins"}):
        config = _make_config({
            commons_constants.CONFIG_SYNC: {
                commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET: "stored-loses"
            }
        })

        assert server.get_or_generate_encryption_secret(config) == "env-wins"
        config.save.assert_not_called()
