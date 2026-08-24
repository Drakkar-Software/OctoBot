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

"""Tests for create_sync_client's base_url composition.

Guards against the mount-path doubling regression: create_sync_client appends
SYNC_MOUNT_PATH itself, so callers MUST pass a bare origin.
"""

import octobot_sync.client as sync_client
import octobot_sync.constants as constants

# Well-known Hardhat test key #1 — public, safe to embed in tests.
_TEST_PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"


def test_create_sync_client_appends_mount_path_once_to_a_bare_origin():
    client, _user_id = sync_client.create_sync_client(
        _TEST_PRIVATE_KEY, sync_url="https://prod-sync.drakkar.software"
    )
    assert client._base_url == f"https://prod-sync.drakkar.software/{constants.SYNC_MOUNT_PATH}"


def test_create_sync_client_strips_a_trailing_slash_before_appending_mount_path():
    client, _user_id = sync_client.create_sync_client(
        _TEST_PRIVATE_KEY, sync_url="https://prod-sync.drakkar.software/"
    )
    assert client._base_url == f"https://prod-sync.drakkar.software/{constants.SYNC_MOUNT_PATH}"


def test_create_sync_client_does_not_double_an_already_suffixed_origin():
    # Documents the actual (buggy) behavior for an already-suffixed sync_url.
    client, _user_id = sync_client.create_sync_client(
        _TEST_PRIVATE_KEY, sync_url="https://prod-sync.drakkar.software/sync"
    )
    assert client._base_url == "https://prod-sync.drakkar.software/sync/sync"
