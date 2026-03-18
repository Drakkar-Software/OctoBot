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

"""Tests for StarfishAuthProvider."""

import time

import pytest

import octobot_sync.auth as auth
import octobot_sync.chain.evm as evm
import octobot_sync.constants as constants


@pytest.fixture
def wallet():
    return evm.create_evm_wallet()


@pytest.fixture
def provider(wallet):
    return auth.StarfishAuthProvider(wallet.private_key, "evm:8453")


def test_address_matches_private_key(wallet, provider):
    assert provider.address == evm.address_from_evm_key(wallet.private_key)


async def test_call_returns_all_headers(provider):
    headers = await provider(method="GET", path="/v1/pull/test", body=None)
    expected_keys = {
        constants.HEADER_PUBKEY,
        constants.HEADER_SIGNATURE,
        constants.HEADER_TIMESTAMP,
        constants.HEADER_NONCE,
        constants.HEADER_CHAIN,
    }
    assert set(headers.keys()) == expected_keys


async def test_signature_is_verifiable(wallet, provider):
    headers = await provider(method="POST", path="/v1/push/test", body='{"data": 1}')
    body_hash = auth.hash_body('{"data": 1}')
    canonical = auth.build_canonical(
        "POST",
        "/v1/push/test",
        headers[constants.HEADER_TIMESTAMP],
        headers[constants.HEADER_NONCE],
        body_hash,
    )
    assert evm.verify_evm(canonical, headers[constants.HEADER_SIGNATURE], wallet.address) is True


async def test_nonce_unique_per_call(provider):
    h1 = await provider(method="GET", path="/", body=None)
    h2 = await provider(method="GET", path="/", body=None)
    assert h1[constants.HEADER_NONCE] != h2[constants.HEADER_NONCE]


async def test_timestamp_is_current(provider):
    before_ms = int(time.time() * 1000)
    headers = await provider(method="GET", path="/", body=None)
    after_ms = int(time.time() * 1000)
    ts = int(headers[constants.HEADER_TIMESTAMP])
    assert before_ms <= ts <= after_ms
