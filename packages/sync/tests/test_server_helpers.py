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

"""Tests for server.py helper functions.

get_or_generate_encryption_secret was removed in the v3 migration; those tests
are gone. The remaining helpers (_require_env) are still present.
"""

import os

import pytest

import octobot_sync.server as server


def test_require_env_present():
    with pytest.MonkeyPatch().context() as mp:
        mp.setenv("TEST_SYNC_VAR", "hello")
        assert server._require_env("TEST_SYNC_VAR") == "hello"


def test_require_env_missing():
    with pytest.MonkeyPatch().context() as mp:
        mp.delenv("TEST_SYNC_VAR", raising=False)
        with pytest.raises(RuntimeError, match="TEST_SYNC_VAR"):
            server._require_env("TEST_SYNC_VAR")
