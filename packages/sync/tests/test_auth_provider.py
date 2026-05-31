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

"""Tests for WalletCapProvider (Starfish v3 cap-cert auth)."""

import pytest

import octobot_sync.auth as auth
import octobot_sync.constants as constants


# Well-known Hardhat test key #1 — public, safe to embed in tests.
_TEST_PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
_ALT_CHALLENGE = "octobot:sync-bootstrap-alt"


@pytest.fixture
def provider():
    return auth.WalletCapProvider(_TEST_PRIVATE_KEY)


def test_user_id_is_string(provider):
    assert isinstance(provider.user_id, str)
    assert len(provider.user_id) > 0


def test_user_id_is_stable_for_same_key(provider):
    """Same key + same challenge must always produce the same user_id."""
    second = auth.WalletCapProvider(_TEST_PRIVATE_KEY)
    assert provider.user_id == second.user_id


def test_user_id_differs_for_different_challenge():
    """Different challenge => different derived identity => different user_id."""
    default_provider = auth.WalletCapProvider(_TEST_PRIVATE_KEY)
    alt_provider = auth.WalletCapProvider(_TEST_PRIVATE_KEY, challenge=_ALT_CHALLENGE)
    assert default_provider.user_id != alt_provider.user_id


async def test_get_cap_returns_cap_dict(provider):
    result = await provider.get_cap()
    assert isinstance(result, dict)
    assert "cap" in result
    assert "dev_ed_priv_hex" in result


async def test_get_cap_kind_is_device(provider):
    result = await provider.get_cap()
    cap = result["cap"]
    assert isinstance(cap, dict)
    assert cap.get("kind") == "device"


async def test_get_cap_iss_user_id_matches_provider_user_id(provider):
    result = await provider.get_cap()
    cap = result["cap"]
    assert cap.get("issUserId") == provider.user_id


async def test_get_cap_is_callable_multiple_times(provider):
    """get_cap() must be callable repeatedly (mint fresh cap each time)."""
    cap1 = await provider.get_cap()
    cap2 = await provider.get_cap()
    assert cap1["cap"]["kind"] == "device"
    assert cap2["cap"]["kind"] == "device"


def test_derive_user_id_matches_provider_user_id():
    uid_via_func = auth.derive_user_id(_TEST_PRIVATE_KEY)
    uid_via_provider = auth.WalletCapProvider(_TEST_PRIVATE_KEY).user_id
    assert uid_via_func == uid_via_provider


def test_derive_root_identity_returns_root_identity():
    root = auth.derive_root_identity(_TEST_PRIVATE_KEY)
    assert hasattr(root, "user_id")
    assert root.user_id == auth.derive_user_id(_TEST_PRIVATE_KEY)


def test_derive_user_id_custom_challenge():
    uid_default = auth.derive_user_id(_TEST_PRIVATE_KEY)
    uid_alt = auth.derive_user_id(_TEST_PRIVATE_KEY, challenge=_ALT_CHALLENGE)
    assert uid_default != uid_alt
