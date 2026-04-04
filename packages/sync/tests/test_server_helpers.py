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

import pytest

import octobot_sync.server as server


def test_require_env_present(monkeypatch):
    monkeypatch.setenv("TEST_SYNC_VAR", "hello")
    assert server._require_env("TEST_SYNC_VAR") == "hello"


def test_require_env_missing(monkeypatch):
    monkeypatch.delenv("TEST_SYNC_VAR", raising=False)
    with pytest.raises(RuntimeError, match="TEST_SYNC_VAR"):
        server._require_env("TEST_SYNC_VAR")
