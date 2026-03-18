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
import octobot_sync.chain.evm as evm


def test_require_env_present(monkeypatch):
    monkeypatch.setenv("TEST_SYNC_VAR", "hello")
    assert server._require_env("TEST_SYNC_VAR") == "hello"


def test_require_env_missing(monkeypatch):
    monkeypatch.delenv("TEST_SYNC_VAR", raising=False)
    with pytest.raises(RuntimeError, match="TEST_SYNC_VAR"):
        server._require_env("TEST_SYNC_VAR")


def test_setup_registry_default(monkeypatch):
    monkeypatch.delenv("EVM_BASE_RPC", raising=False)
    monkeypatch.delenv("EVM_CONTRACT_BASE", raising=False)
    registry = server._setup_registry()
    chain = registry.get("evm:8453")
    assert chain is not None
    assert isinstance(chain, evm.EvmChain)
    assert chain.id == "evm:8453"
    # No contract configured
    with pytest.raises(RuntimeError, match="RPC not configured"):
        chain._require_contract()


def test_setup_registry_with_rpc(monkeypatch):
    monkeypatch.setenv("EVM_BASE_RPC", "https://rpc.example.com")
    monkeypatch.setenv("EVM_CONTRACT_BASE", "0x0000000000000000000000000000000000000001")
    registry = server._setup_registry()
    chain = registry.get("evm:8453")
    assert chain is not None
    # Contract should be configured (no RuntimeError)
    chain._require_contract()
