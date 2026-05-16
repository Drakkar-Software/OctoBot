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

import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider_module
import octobot_node.constants as node_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums


class TestStrategyProviderCollection:
    def test_collection_is_user_strategies(self):
        assert strategy_provider_module.StrategyProvider.COLLECTION == sync_enums.Collections.USER_STRATEGIES.value

    def test_storage_collection_matches(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.Collections.USER_STRATEGIES.value

    def test_storage_is_base_local_collection_storage(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, base_storage_module.BaseLocalCollectionStorage)


class TestStrategyProviderStateFormat:
    def test_state_version_matches_user_strategies_constant(self):
        assert strategy_provider_module.StrategyProvider.STATE_VERSION == node_constants.USER_STRATEGIES_STATE_VERSION

    def test_state_class_is_strategies_state(self):
        assert strategy_provider_module.StrategyProvider.STATE_CLASS is protocol_models.StrategiesState

    def test_items_key_is_strategies(self):
        assert strategy_provider_module.StrategyProvider.ITEMS_KEY == "strategies"


class TestStrategyProviderGetItemId:
    def test_returns_strategy_id(self, tmp_path):
        provider = strategy_provider_module.StrategyProvider(base_folder=str(tmp_path))
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        configuration = protocol_models.GenericProcessConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
            profile_data={},
        )
        strategy = protocol_models.Strategy(
            id="strat-42",
            version="1.0.0",
            name="Test strategy",
            created_at=fixture_time,
            updated_at=fixture_time,
            configuration=protocol_models.StrategyConfiguration(configuration),
        )
        assert provider._get_item_id(strategy) == "strat-42"
