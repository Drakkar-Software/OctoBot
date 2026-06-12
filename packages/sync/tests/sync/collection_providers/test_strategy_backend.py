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

import json

import mock

import octobot.community.authentication as community_authentication
import octobot_sync.crypto as sync_crypto
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider_module
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums


_TEST_ADDRESS = "0xaaabbbcccddd"
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


def _legacy_grid_strategy_state_json() -> str:
    return json.dumps(
        {
            "version": sync_constants.USER_STRATEGIES_STATE_VERSION,
            "strategies": [
                {
                    "id": "strat-legacy",
                    "version": "1",
                    "reference_market": "USDC",
                    "configuration": {
                        "configuration_type": "grid",
                        "pair_settings": None,
                        "name": None,
                        "config": None,
                    },
                }
            ],
        }
    )


def _persist_encrypted_legacy_strategy_state(
    tmp_path,
    address: str,
    private_key: str,
) -> None:
    collection = sync_enums.TemporaryCollections.TEMP_USER_STRATEGIES.value
    blob = sync_crypto.encrypt_bytes_to_blob_dict(
        _legacy_grid_strategy_state_json().encode("utf-8"),
        private_key,
        collection,
    )
    path = tmp_path / collection / f"{address}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(blob, handle)


class TestStrategyProviderCollection:
    def test_collection_is_user_strategies(self):
        assert strategy_provider_module.StrategyProvider.COLLECTION == sync_enums.TemporaryCollections.TEMP_USER_STRATEGIES.value

    def test_storage_collection_matches(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.TemporaryCollections.TEMP_USER_STRATEGIES.value

    def test_storage_is_base_local_collection_storage(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, base_storage_module.BaseLocalCollectionStorage)


class TestStrategyProviderStateFormat:
    def test_state_version_matches_user_strategies_constant(self):
        assert strategy_provider_module.StrategyProvider.STATE_VERSION == sync_constants.USER_STRATEGIES_STATE_VERSION

    def test_state_class_is_strategies_state(self):
        assert strategy_provider_module.StrategyProvider.STATE_CLASS is protocol_models.StrategiesState

    def test_items_key_is_strategies(self):
        assert strategy_provider_module.StrategyProvider.ITEMS_KEY == "strategies"


class TestStrategyProviderGetItemId:
    def test_returns_strategy_id(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        strategy = mock.Mock()
        strategy.id = "strat-42"
        assert provider._get_item_id(strategy) == "strat-42"


class TestStrategyProviderListItems:
    def test_list_items_loads_legacy_grid_configuration(self, tmp_path):
        _persist_encrypted_legacy_strategy_state(
            tmp_path,
            _TEST_ADDRESS,
            _TEST_PRIVATE_KEY,
        )
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        with _patch_wallet():
            strategies = provider.list_items(_TEST_ADDRESS)

        assert len(strategies) == 1
        assert strategies[0].id == "strat-legacy"
        assert strategies[0].reference_market == "USDC"
        assert strategies[0].configuration.actual_instance is None
