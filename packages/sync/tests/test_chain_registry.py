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

"""Tests for ChainRegistry."""

import pytest

import octobot_sync.chain as sync_chain
import tests.mock_chain as mock_chain_module


def test_register_and_get():
    registry = sync_chain.ChainRegistry()
    mock = mock_chain_module.MockChain("test-chain")
    registry.register(mock)
    assert registry.get("test-chain") is mock


def test_get_unknown_raises():
    registry = sync_chain.ChainRegistry()
    with pytest.raises(ValueError, match="Unknown chain"):
        registry.get("nonexistent")


def test_list():
    registry = sync_chain.ChainRegistry()
    chain1 = mock_chain_module.MockChain("chain-1")
    chain2 = mock_chain_module.MockChain("chain-2")
    registry.register(chain1)
    registry.register(chain2)
    chains = registry.list()
    assert len(chains) == 2
    assert chain1 in chains
    assert chain2 in chains


def test_register_overwrites():
    registry = sync_chain.ChainRegistry()
    chain1 = mock_chain_module.MockChain("same-id")
    chain2 = mock_chain_module.MockChain("same-id")
    registry.register(chain1)
    registry.register(chain2)
    assert registry.get("same-id") is chain2
