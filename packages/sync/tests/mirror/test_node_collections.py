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

"""Tests for the node's mirror-eligible-collection reader dispatcher.

Providers are mocked at their `.instance()` singleton accessor rather than
hitting real disk/wallet storage — this module is a thin dispatcher, its
only job is "call the right provider method and shape the result as a
dict," which doesn't need real persistence to verify.
"""

from unittest import mock

import pytest

import octobot_sync.mirror.node_collections as node_collections
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module
import octobot_sync.sync.collection_providers.user_account_trading_provider as trading_provider_module
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider_module

_USER_ID = "user-1"


def _model(**fields):
    m = mock.Mock()
    m.model_dump.return_value = fields
    return m


@pytest.mark.asyncio
async def test_reads_user_accounts_from_the_account_provider():
    provider = mock.Mock()
    provider.list_accounts.return_value = [_model(id="acc-1")]
    provider.list_exchange_configs.return_value = [_model(id="cfg-1")]
    with mock.patch.object(account_provider_module.AccountProvider, "instance", return_value=provider):
        result = await node_collections.read_node_collection("user-accounts", _USER_ID)
    provider.list_accounts.assert_called_once_with(_USER_ID)
    provider.list_exchange_configs.assert_called_once_with(_USER_ID)
    assert result == {"accounts": [{"id": "acc-1"}], "exchange_configs": [{"id": "cfg-1"}]}


@pytest.mark.asyncio
async def test_reads_trading_state_for_every_account():
    accounts = mock.Mock()
    accounts.list_accounts.return_value = [mock.Mock(id="acc-1"), mock.Mock(id="acc-2")]
    trading = mock.Mock()
    trading.load_state.side_effect = [
        mock.Mock(account_trading=_model(state="s1")),
        mock.Mock(account_trading=_model(state="s2")),
    ]
    with mock.patch.object(
        account_provider_module.AccountProvider, "instance", return_value=accounts
    ), mock.patch.object(
        trading_provider_module.AccountTradingProvider, "instance", return_value=trading
    ):
        result = await node_collections.read_node_collection("user-accounts-trading", _USER_ID)
    assert trading.load_state.call_args_list == [
        mock.call(_USER_ID, "acc-1"),
        mock.call(_USER_ID, "acc-2"),
    ]
    # Same wire shape the mobile writer produces — both feed one mirror, so a
    # reader must never see two shapes.
    assert result == {
        "account_tradings": [
            {"account_id": "acc-1", "account_trading": {"state": "s1"}},
            {"account_id": "acc-2", "account_trading": {"state": "s2"}},
        ]
    }


@pytest.mark.asyncio
async def test_accounts_that_never_traded_are_skipped_not_fatal():
    accounts = mock.Mock()
    accounts.list_accounts.return_value = [mock.Mock(id="acc-1"), mock.Mock(id="acc-2")]
    trading = mock.Mock()
    trading.load_state.side_effect = [
        collection_errors.CollectionNoDataError(),
        mock.Mock(account_trading=_model(state="s2")),
    ]
    with mock.patch.object(
        account_provider_module.AccountProvider, "instance", return_value=accounts
    ), mock.patch.object(
        trading_provider_module.AccountTradingProvider, "instance", return_value=trading
    ):
        result = await node_collections.read_node_collection("user-accounts-trading", _USER_ID)
    assert result == {
        "account_tradings": [{"account_id": "acc-2", "account_trading": {"state": "s2"}}]
    }


@pytest.mark.asyncio
async def test_reads_user_strategies_from_the_strategy_provider():
    provider = mock.Mock()
    provider.list_items.return_value = [_model(id="strat-1")]
    with mock.patch.object(
        strategy_provider_module.StrategyProvider, "instance", return_value=provider
    ):
        result = await node_collections.read_node_collection("user-strategies", _USER_ID)
    provider.list_items.assert_called_once_with(_USER_ID)
    assert result == {"items": [{"id": "strat-1"}]}


@pytest.mark.asyncio
async def test_user_data_raises_not_implemented_rather_than_a_silent_empty_mirror():
    with pytest.raises(NotImplementedError):
        await node_collections.read_node_collection("user-data", _USER_ID)


@pytest.mark.asyncio
async def test_unknown_collection_raises_value_error():
    with pytest.raises(ValueError):
        await node_collections.read_node_collection("not-a-real-collection", _USER_ID)


@pytest.mark.asyncio
async def test_empty_accounts_and_configs_still_return_the_dict_shape():
    provider = mock.Mock()
    provider.list_accounts.return_value = []
    provider.list_exchange_configs.return_value = []
    with mock.patch.object(account_provider_module.AccountProvider, "instance", return_value=provider):
        result = await node_collections.read_node_collection("user-accounts", _USER_ID)
    assert result == {"accounts": [], "exchange_configs": []}
