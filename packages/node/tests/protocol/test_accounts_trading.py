#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import mock

import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot_node.protocol.accounts_trading as accounts_trading_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
_TEST_ACCOUNT_ID = "acc-trading-1"
_SAMPLE_ENCRYPTED_BLOB = {
    sync_constants.BLOB_IV_KEY: "sample-iv",
    sync_constants.BLOB_DATA_KEY: "sample-data",
}


class TestGetAccountTradingStateEncrypted:
    """Checks :func:`octobot_node.protocol.accounts_trading.get_account_trading_state_encrypted`."""

    def test_passes_address_and_account_id_to_provider_and_returns_blob(self):
        provider_stub = mock.Mock()
        provider_stub.load_state_encrypted = mock.Mock(return_value=_SAMPLE_ENCRYPTED_BLOB)
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            encrypted_state = accounts_trading_module.get_account_trading_state_encrypted(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
            )

        provider_stub.load_state_encrypted.assert_called_once_with(
            _TEST_WALLET_ADDRESS,
            _TEST_ACCOUNT_ID,
        )
        assert encrypted_state == _SAMPLE_ENCRYPTED_BLOB

    def test_returns_none_when_provider_raises_collection_no_data_error(self):
        provider_stub = mock.Mock()
        provider_stub.load_state_encrypted = mock.Mock(
            side_effect=collection_errors.CollectionNoDataError("missing trading state"),
        )
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            encrypted_state = accounts_trading_module.get_account_trading_state_encrypted(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
            )

        assert encrypted_state is None
