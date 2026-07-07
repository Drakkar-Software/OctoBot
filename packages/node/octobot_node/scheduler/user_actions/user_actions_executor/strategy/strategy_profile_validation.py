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
import octobot_protocol.models.generic_process_configuration as generic_process_configuration

import octobot_node.errors as node_errors


def validate_profile_strategy_configuration(
    strategy: protocol_models.Strategy,
) -> None:
    configuration = strategy.configuration
    if configuration is None or configuration.actual_instance is None:
        return
    if not isinstance(
        configuration.actual_instance,
        generic_process_configuration.GenericProcessConfiguration,
    ):
        return
    generic_configuration = configuration.actual_instance
    if generic_configuration.profile_data is None:
        return
    profile_details = dict(
        generic_configuration.profile_data.get("profile_details") or {}
    )
    profile_id = profile_details.get("id")
    if profile_id is None:
        profile_details["id"] = strategy.id
        generic_configuration.profile_data["profile_details"] = profile_details
        return
    if profile_id != strategy.id:
        raise node_errors.InvalidUserActionPayloadError(
            "profile_data.profile_details.id must match strategy.id."
        )
