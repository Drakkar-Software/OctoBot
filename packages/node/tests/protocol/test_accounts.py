#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import datetime

import mock

import octobot_protocol.models as protocol_models

import octobot_sync.constants as sync_constants
import octobot_node.protocol.accounts as accounts_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


class TestGetAccountsState:
    """Checks :func:`octobot_node.protocol.accounts.get_accounts_state`."""

    def test_passes_address_to_provider_and_returns_exchange_accounts_version(self):
        sample_timestamp = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        sample_accounts = [
            protocol_models.Account(
                id="acc-a",
                name="Alpha",
                is_simulated=False,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
            ),
        ]
        sample_exchange_configs = [
            protocol_models.ExchangeConfig(
                id="cfg-a",
                name="binance-main",
                exchange="binance",
                sandboxed=False,
            ),
        ]
        provider_stub = mock.Mock()
        provider_stub.list_items = mock.Mock(return_value=sample_accounts)
        provider_stub.list_exchange_configs = mock.Mock(return_value=sample_exchange_configs)
        with mock.patch.object(
            accounts_module.account_provider.AccountProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_state = accounts_module.get_accounts_state(_TEST_WALLET_ADDRESS)
        provider_stub.list_items.assert_called_once_with(_TEST_WALLET_ADDRESS)
        provider_stub.list_exchange_configs.assert_called_once_with(_TEST_WALLET_ADDRESS)
        assert accounts_state.version == sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION
        assert accounts_state.accounts == sample_accounts
        assert accounts_state.exchange_configs == sample_exchange_configs
        assert isinstance(accounts_state, protocol_models.AccountsState)

    def test_empty_accounts_when_provider_returns_empty_list(self):
        provider_stub = mock.Mock()
        provider_stub.list_items = mock.Mock(return_value=[])
        provider_stub.list_exchange_configs = mock.Mock(return_value=[])
        with mock.patch.object(
            accounts_module.account_provider.AccountProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_state = accounts_module.get_accounts_state(_TEST_WALLET_ADDRESS)
        assert accounts_state.accounts == []
        assert accounts_state.exchange_configs == []

    def test_returns_exchange_configs_from_provider(self):
        sample_exchange_configs = [
            protocol_models.ExchangeConfig(
                id="cfg-1",
                name="kraken-main",
                exchange="kraken",
                sandboxed=True,
            ),
        ]
        provider_stub = mock.Mock()
        provider_stub.list_items = mock.Mock(return_value=[])
        provider_stub.list_exchange_configs = mock.Mock(return_value=sample_exchange_configs)
        with mock.patch.object(
            accounts_module.account_provider.AccountProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_state = accounts_module.get_accounts_state(_TEST_WALLET_ADDRESS)
        assert accounts_state.exchange_configs == sample_exchange_configs
