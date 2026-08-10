#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import datetime
import json

import mock
import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage_module
import octobot_sync.sync.collection_providers.user_account_history_provider as history_provider_module
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums
import octobot_sync.sync.collection_backend.errors as collection_errors

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_ACCOUNT_ID = "acc-42"
_TEST_PRIVATE_KEY = "private-key"


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet_by_user_id.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


def _sample_history_state(updated_at: datetime.datetime) -> protocol_models.PortfolioHistoricalValuesState:
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=protocol_models.PortfolioHistoricalValues(
            unit="USDT",
            values=[
                protocol_models.PortfolioHistoricalValue(
                    timestamp=updated_at,
                    total=1000.0,
                )
            ],
        ),
    )


class TestAccountHistoryProviderCollection:
    def test_collection_is_USER_ACCOUNTS_HISTORY(self):
        assert (
            history_provider_module.AccountHistoryProvider.COLLECTION
            == sync_enums.Collections.USER_ACCOUNTS_HISTORY.value
        )

    def test_storage_collection_matches(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.Collections.USER_ACCOUNTS_HISTORY.value

    def test_storage_is_single_item_local_collection_storage(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, single_item_storage_module.SingleItemLocalCollectionStorage)


class TestAccountHistoryProviderStateFormat:
    def test_state_version_matches_constant(self):
        assert (
            history_provider_module.AccountHistoryProvider.STATE_VERSION
            == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        )

    def test_state_class_is_portfolio_historical_values_state(self):
        assert (
            history_provider_module.AccountHistoryProvider.STATE_CLASS
            is protocol_models.PortfolioHistoricalValuesState
        )


class TestAccountHistoryProviderLoadSaveState:
    def test_save_and_load_state_per_account_id(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        history_state = _sample_history_state(fixture_time)
        updated_time = datetime.datetime(2026, 1, 16, tzinfo=datetime.UTC)
        updated_state = _sample_history_state(updated_time)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, history_state)
            loaded_state = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, updated_state)
            reloaded_state = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        assert loaded_state.history.values[0].timestamp == fixture_time
        assert reloaded_state.history.values[0].timestamp == updated_time

    def test_load_state_encrypted_reads_persisted_blob(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        history_state = _sample_history_state(fixture_time)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, history_state)
            encrypted_blob = provider.load_state_encrypted(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        assert "iv" in encrypted_blob
        assert "data" in encrypted_blob


class TestAccountHistoryProviderSeparateFiles:
    def test_accounts_use_separate_files(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        first_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        second_time = datetime.datetime(2026, 1, 16, tzinfo=datetime.UTC)
        first_state = _sample_history_state(first_time)
        second_state = _sample_history_state(second_time)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, "acc-1", first_state)
            provider.save_state(_TEST_ADDRESS, "acc-2", second_state)
            loaded_first = provider.load_state(_TEST_ADDRESS, "acc-1")
            loaded_second = provider.load_state(_TEST_ADDRESS, "acc-2")
        assert loaded_first.history.values[0].timestamp == first_time
        assert loaded_second.history.values[0].timestamp == second_time


class TestAccountHistoryProviderMissingState:
    def test_load_state_raises_when_file_missing(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        with _patch_wallet():
            try:
                provider.load_state(_TEST_ADDRESS, "missing-account")
                raise AssertionError("Expected CollectionNoDataError")
            except collection_errors.CollectionNoDataError:
                pass


class TestAccountHistoryProviderWalletKey:
    def test_save_requires_wallet_private_key(self, tmp_path):
        provider = history_provider_module.AccountHistoryProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        history_state = _sample_history_state(fixture_time)
        auth = mock.Mock()
        auth.get_wallet_by_user_id.side_effect = KeyError("wallet not found")
        with mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=auth,
        ):
            try:
                provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, history_state)
                raise AssertionError("Expected KeyError from missing wallet")
            except KeyError:
                pass
