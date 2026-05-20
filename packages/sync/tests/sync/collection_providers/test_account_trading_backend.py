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

import datetime

import mock
import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage_module
import octobot_sync.sync.collection_providers.user_account_trading_provider as trading_provider_module
import octobot_node.constants as node_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_ACCOUNT_ID = "acc-42"
_TEST_PRIVATE_KEY = "private-key"


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


class TestAccountTradingProviderCollection:
    def test_collection_is_USER_ACCOUNTS_TRADING(self):
        assert (
            trading_provider_module.AccountTradingProvider.COLLECTION
            == sync_enums.Collections.USER_ACCOUNTS_TRADING.value
        )

    def test_storage_collection_matches(self, tmp_path):
        provider = trading_provider_module.AccountTradingProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.Collections.USER_ACCOUNTS_TRADING.value

    def test_storage_is_single_item_local_collection_storage(self, tmp_path):
        provider = trading_provider_module.AccountTradingProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, single_item_storage_module.SingleItemLocalCollectionStorage)


class TestAccountTradingProviderStateFormat:
    def test_state_version_matches_constant(self):
        assert (
            trading_provider_module.AccountTradingProvider.STATE_VERSION
            == node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION
        )

    def test_state_class_is_account_trading_state(self):
        assert (
            trading_provider_module.AccountTradingProvider.STATE_CLASS
            is protocol_models.AccountTradingState
        )


class TestAccountTradingProviderLoadSaveState:
    def test_save_and_load_state_per_account_id(self, tmp_path):
        provider = trading_provider_module.AccountTradingProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        account_trading = protocol_models.AccountTrading(
            updated_at=fixture_time,
        )
        trading_state = protocol_models.AccountTradingState(
            version=node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=[account_trading],
        )
        updated_time = datetime.datetime(2026, 1, 16, tzinfo=datetime.UTC)
        updated_account_trading = protocol_models.AccountTrading(
            updated_at=updated_time,
        )
        updated_state = protocol_models.AccountTradingState(
            version=node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=[updated_account_trading],
        )
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, trading_state)
            loaded_state = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, updated_state)
            reloaded_state = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        assert loaded_state.account_trading[0].updated_at == fixture_time
        assert reloaded_state.account_trading[0].updated_at == updated_time

    def test_load_state_encrypted_reads_persisted_blob(self, tmp_path):
        provider = trading_provider_module.AccountTradingProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        trading_state = protocol_models.AccountTradingState(
            version=node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=[
                protocol_models.AccountTrading(
                    updated_at=fixture_time,
                )
            ],
        )
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, trading_state)
            encrypted_blob = provider.load_state_encrypted(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        assert "iv" in encrypted_blob
        assert "data" in encrypted_blob

    def test_accounts_use_separate_files(self, tmp_path):
        provider = trading_provider_module.AccountTradingProvider(base_folder=str(tmp_path))
        first_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        second_time = datetime.datetime(2026, 1, 16, tzinfo=datetime.UTC)
        first_state = protocol_models.AccountTradingState(
            version=node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=[
                protocol_models.AccountTrading(
                    updated_at=first_time,
                )
            ],
        )
        second_state = protocol_models.AccountTradingState(
            version=node_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=[
                protocol_models.AccountTrading(
                    updated_at=second_time,
                )
            ],
        )
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, "acc-1", first_state)
            provider.save_state(_TEST_ADDRESS, "acc-2", second_state)
            loaded_first = provider.load_state(_TEST_ADDRESS, "acc-1")
            loaded_second = provider.load_state(_TEST_ADDRESS, "acc-2")
        assert loaded_first == first_state
        assert loaded_second == second_state
