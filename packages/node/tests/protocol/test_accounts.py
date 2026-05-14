#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import mock

import octobot_protocol.models as protocol_models

import octobot_node.constants as node_constants
import octobot_node.protocol.accounts as accounts_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


class TestGetAccountsState:
    """Checks :func:`octobot_node.protocol.accounts.get_accounts_state`."""

    def test_passes_address_to_provider_and_returns_exchange_accounts_version(self):
        sample_accounts = [
            protocol_models.Account(id="acc-a", name="Alpha", is_simulated=False),
        ]
        provider_stub = mock.Mock()
        provider_stub.list_items = mock.Mock(return_value=sample_accounts)
        with mock.patch.object(
            accounts_module.account_provider.AccountProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_state = accounts_module.get_accounts_state(_TEST_WALLET_ADDRESS)
        provider_stub.list_items.assert_called_once_with(_TEST_WALLET_ADDRESS)
        assert accounts_state.version == node_constants.EXCHANGE_ACCOUNTS_STATE_VERSION
        assert accounts_state.accounts == sample_accounts
        assert isinstance(accounts_state, protocol_models.AccountsState)

    def test_empty_accounts_when_provider_returns_empty_list(self):
        provider_stub = mock.Mock()
        provider_stub.list_items = mock.Mock(return_value=[])
        with mock.patch.object(
            accounts_module.account_provider.AccountProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_state = accounts_module.get_accounts_state(_TEST_WALLET_ADDRESS)
        assert accounts_state.accounts == []
