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
from unittest.mock import MagicMock

import mock
import pytest

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

_TEST_ADDRESS = "0xaaabbbcccddd"
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


def _make_provider(tmp_path):
    return account_provider_module.AccountProvider(base_folder=str(tmp_path))


def _fixture_time() -> datetime.datetime:
    return datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)


def _sample_account(account_id: str = "acc-1", name: str = "Test") -> protocol_models.Account:
    fixture_time = _fixture_time()
    return protocol_models.Account(
        id=account_id,
        name=name,
        is_simulated=False,
        created_at=fixture_time,
        updated_at=fixture_time,
    )


def _sample_exchange_config(
    config_id: str = "cfg-1",
    name: str = "binance-main",
    exchange: str = "binance",
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=config_id,
        name=name,
        exchange=exchange,
        sandboxed=False,
    )


class TestAccountProviderCollection:
    def test_collection_is_user_accounts(self):
        assert account_provider_module.AccountProvider.COLLECTION == sync_enums.Collections.USER_ACCOUNTS.value

    def test_storage_collection_matches(self, tmp_path):
        provider = _make_provider(tmp_path)
        assert provider._storage.collection == sync_enums.Collections.USER_ACCOUNTS.value

    def test_storage_is_base_local_collection_storage(self, tmp_path):
        provider = _make_provider(tmp_path)
        assert isinstance(provider._storage, base_storage_module.BaseLocalCollectionStorage)


class TestAccountProviderStateFormat:
    def test_state_version_matches_exchange_accounts_constant(self):
        assert account_provider_module.AccountProvider.STATE_VERSION == sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION

    def test_state_class_is_accounts_state(self):
        assert account_provider_module.AccountProvider.STATE_CLASS is protocol_models.AccountsState

    def test_items_key_is_accounts(self):
        assert account_provider_module.AccountProvider.ITEMS_KEY == "accounts"


class TestAccountProviderGetItemId:
    def test_returns_account_id(self, tmp_path):
        provider = _make_provider(tmp_path)
        assert provider._get_item_id(_sample_account("acc-42")) == "acc-42"


class TestAccountProviderExchangeConfigGetItemId:
    def test_returns_exchange_config_id(self, tmp_path):
        provider = _make_provider(tmp_path)
        exchange_config = _sample_exchange_config("cfg-42")
        assert provider._get_item_id_for_key(
            account_provider_module.AccountProvider.EXCHANGE_CONFIGS_KEY,
            exchange_config,
        ) == "cfg-42"


class TestAccountProviderListExchangeConfigs:
    def test_empty_by_default(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            listed = provider.list_exchange_configs(_TEST_ADDRESS)
        assert listed == []

    def test_lists_created_exchange_configs(self, tmp_path):
        provider = _make_provider(tmp_path)
        exchange_config = _sample_exchange_config("cfg-1")
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, exchange_config)
            listed = provider.list_exchange_configs(_TEST_ADDRESS)
        assert len(listed) == 1
        assert listed[0].id == "cfg-1"


class TestAccountProviderCreateExchangeConfig:
    def test_persists_exchange_config(self, tmp_path):
        provider = _make_provider(tmp_path)
        exchange_config = _sample_exchange_config("cfg-1")
        with _patch_wallet():
            created = provider.create_exchange_config(_TEST_ADDRESS, exchange_config)
        assert created.id == "cfg-1"

    def test_duplicate_id_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        exchange_config = _sample_exchange_config("cfg-1")
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, exchange_config)
        with pytest.raises(collection_errors.DuplicateItemError):
            with _patch_wallet():
                provider.create_exchange_config(_TEST_ADDRESS, exchange_config)


class TestAccountProviderGetExchangeConfig:
    def test_returns_matching_exchange_config(self, tmp_path):
        provider = _make_provider(tmp_path)
        exchange_config = _sample_exchange_config("cfg-1", name="binance-main")
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, exchange_config)
            fetched = provider.get_exchange_config(_TEST_ADDRESS, "cfg-1")
        assert fetched.name == "binance-main"

    def test_missing_exchange_config_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.ItemNotFoundError):
            with _patch_wallet():
                provider.get_exchange_config(_TEST_ADDRESS, "missing")


class TestAccountProviderUpdateExchangeConfig:
    def test_updates_existing_exchange_config(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config("cfg-1", name="Original"))
            provider.update_exchange_config(
                _TEST_ADDRESS,
                _sample_exchange_config("cfg-1", name="Updated"),
            )
            fetched = provider.get_exchange_config(_TEST_ADDRESS, "cfg-1")
        assert fetched.name == "Updated"


class TestAccountProviderDeleteExchangeConfig:
    def test_deletes_existing_exchange_config(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config("cfg-1"))
            provider.delete_exchange_config(_TEST_ADDRESS, "cfg-1")
            listed = provider.list_exchange_configs(_TEST_ADDRESS)
        assert listed == []


class TestAccountProviderCrossCollectionPersistence:
    def test_account_update_preserves_exchange_configs(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_account(_TEST_ADDRESS, _sample_account("acc-1", name="Original"))
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config("cfg-1", name="binance-main"))
            provider.update_account(_TEST_ADDRESS, _sample_account("acc-1", name="Updated"))

        state = provider._storage.load_state(
            _TEST_ADDRESS,
            _TEST_PRIVATE_KEY,
            protocol_models.AccountsState,
        )
        assert state.accounts[0].name == "Updated"
        assert len(state.exchange_configs) == 1
        assert state.exchange_configs[0].id == "cfg-1"

    def test_exchange_config_update_preserves_accounts(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_account(_TEST_ADDRESS, _sample_account("acc-1", name="Alpha"))
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config("cfg-1", name="Original"))
            provider.update_exchange_config(
                _TEST_ADDRESS,
                _sample_exchange_config("cfg-1", name="Updated"),
            )

        state = provider._storage.load_state(
            _TEST_ADDRESS,
            _TEST_PRIVATE_KEY,
            protocol_models.AccountsState,
        )
        assert state.accounts[0].name == "Alpha"
        assert state.exchange_configs[0].name == "Updated"
