#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider
import octobot_sync.sync.collection_backend.errors as collection_errors


def get_strategies_state_encrypted(user_id: str) -> dict[str, str] | None:
    try:
        return strategy_provider.StrategyProvider.instance().list_items_encrypted(user_id)
    except collection_errors.CollectionNoDataError:
        return None

def get_strategies_state(user_id: str) -> protocol_models.StrategiesState:
    provider = strategy_provider.StrategyProvider.instance()
    return protocol_models.StrategiesState(
        version=sync_constants.USER_STRATEGIES_STATE_VERSION,
        strategies=provider.list_items(user_id),
    )
