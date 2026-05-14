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
import octobot_node.constants as node_constants
import octobot_node.scheduler.api as scheduler_api


async def get_user_data_state(wallet_address: str) -> protocol_models.UserDataState:
    automations = await scheduler_api.get_automation_states(wallet_address)
    user_actions = await scheduler_api.list_user_actions(wallet_address)
    return protocol_models.UserDataState(
        version=node_constants.USER_DATA_STATE_VERSION,
        automations=automations,
        user_actions=user_actions,
    )
