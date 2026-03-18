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

"""Tests for EVM crypto functions and EvmChain."""

from unittest.mock import AsyncMock

import pytest
from web3 import Web3

import octobot_sync.chain.evm as evm


def test_create_evm_wallet():
    wallet = evm.create_evm_wallet()
    # key.hex() returns 64 hex chars (no 0x prefix)
    assert len(wallet.private_key) == 64
    assert all(c in "0123456789abcdef" for c in wallet.private_key)
    assert Web3.is_checksum_address(wallet.address)


def test_address_from_evm_key():
    wallet = evm.create_evm_wallet()
    derived = evm.address_from_evm_key(wallet.private_key)
    assert derived == wallet.address


def test_eip191_hash_deterministic():
    h1 = evm._eip191_hash("hello")
    h2 = evm._eip191_hash("hello")
    h3 = evm._eip191_hash("world")
    assert h1 == h2
    assert h1 != h3


def test_verify_evm_valid_signature():
    w3 = Web3()
    wallet = evm.create_evm_wallet()
    message = "test-canonical-string"
    msg_hash = evm._eip191_hash(message)
    signed = w3.eth.account._sign_hash(msg_hash, private_key=wallet.private_key)
    assert evm.verify_evm(message, signed.signature.hex(), wallet.address) is True


def test_verify_evm_invalid_signature():
    wallet = evm.create_evm_wallet()
    assert evm.verify_evm("message", "0xdead", wallet.address) is False


def test_verify_evm_wrong_address():
    w3 = Web3()
    wallet = evm.create_evm_wallet()
    other_wallet = evm.create_evm_wallet()
    msg_hash = evm._eip191_hash("msg")
    signed = w3.eth.account._sign_hash(msg_hash, private_key=wallet.private_key)
    assert evm.verify_evm("msg", signed.signature.hex(), other_wallet.address) is False


async def test_async_ttl_cached_returns_cached():
    call_count = 0

    class FakeChain:
        @evm._async_ttl_cached(ttl_s=300)
        async def fetch(self, key):
            nonlocal call_count
            call_count += 1
            return f"result-{key}"

    chain = FakeChain()
    r1 = await chain.fetch("a")
    r2 = await chain.fetch("a")
    assert r1 == r2 == "result-a"
    assert call_count == 1


async def test_async_ttl_cached_different_args():
    call_count = 0

    class FakeChain:
        @evm._async_ttl_cached(ttl_s=300)
        async def fetch(self, key):
            nonlocal call_count
            call_count += 1
            return f"result-{key}"

    chain = FakeChain()
    await chain.fetch("a")
    await chain.fetch("b")
    assert call_count == 2


def test_evm_chain_require_contract_raises():
    chain = evm.EvmChain("evm:8453")  # no RPC
    with pytest.raises(RuntimeError, match="RPC not configured"):
        chain._require_contract()
