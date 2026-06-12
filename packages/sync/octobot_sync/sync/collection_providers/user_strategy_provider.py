#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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


import typing

import octobot_commons.singleton.singleton_class as singleton_class
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_protocol.models.action_configuration_type as protocol_action_configuration_type
import octobot_protocol.models.strategy_configuration as protocol_strategy_configuration
import octobot_sync.enums as sync_enums

import octobot_sync.sync.collection_backend.base_local_collection_provider as base_provider
import octobot_sync.sync.collection_backend.tolerant_state_loading as tolerant_state_loading


def _sanitize_strategy_configuration_dict(
    configuration_dict: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    sanitized_configuration = dict(configuration_dict)
    configuration_type = sanitized_configuration.get("configuration_type")
    valid_configuration_types = {
        member.value for member in protocol_action_configuration_type.ActionConfigurationType
    }
    if (
        configuration_type is not None
        and configuration_type not in valid_configuration_types
    ):
        sanitized_configuration.pop("configuration_type", None)
    return {
        configuration_key: configuration_value
        for configuration_key, configuration_value in sanitized_configuration.items()
        if configuration_value is not None
    }


def _empty_strategy_configuration() -> protocol_strategy_configuration.StrategyConfiguration:
    return protocol_strategy_configuration.StrategyConfiguration.model_construct(
        actual_instance=None,
    )


class StrategyProvider(
    base_provider.BaseLocalCollectionProvider[protocol_models.Strategy, protocol_models.StrategiesState],
    singleton_class.Singleton
):
    """
    Singleton provider exposing CRUD operations on protocol Strategy models.

    Strategies are grouped per wallet address and persisted as an encrypted
    StrategiesState envelope.  All CRUD logic lives in the base class.
    """
    COLLECTION = sync_enums.TemporaryCollections.TEMP_USER_STRATEGIES.value
    STATE_VERSION = sync_constants.USER_STRATEGIES_STATE_VERSION
    STATE_CLASS = protocol_models.StrategiesState
    ITEMS_KEY = "strategies"
    MODEL_SANITIZERS: typing.ClassVar[dict[type, tolerant_state_loading.ModelSanitizer]] = {
        protocol_strategy_configuration.StrategyConfiguration: _sanitize_strategy_configuration_dict,
    }
    MODEL_FALLBACKS: typing.ClassVar[dict[type, tolerant_state_loading.ModelFallback]] = {
        protocol_strategy_configuration.StrategyConfiguration: _empty_strategy_configuration,
    }

    def _get_item_id(self, item: protocol_models.Strategy) -> str:
        return item.id
