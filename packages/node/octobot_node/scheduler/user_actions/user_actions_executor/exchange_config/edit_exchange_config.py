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

import octobot_sync.sync.collection_providers as collection_providers
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.exchange_config.exchange_config_user_action_executor as exchange_config_user_action_executor


def _get_edit_exchange_config_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.EditExchangeConfigConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete edit-exchange-config configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.EditExchangeConfigConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            "EditExchangeConfigActionExecutor expected EditExchangeConfigConfiguration, "
            f"got {type(payload).__name__}"
        )
    return payload


class EditExchangeConfigActionExecutor(
    exchange_config_user_action_executor.ExchangeConfigUserActionExecutor,
):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        edit_payload = _get_edit_exchange_config_payload(user_action)
        if edit_payload.configuration is None:
            raise node_errors.InvalidUserActionPayloadError(
                "EditExchangeConfigConfiguration.configuration is required to update an exchange config."
            )
        if edit_payload.configuration.id != edit_payload.id:
            raise node_errors.InvalidUserActionPayloadError(
                "EditExchangeConfigConfiguration.id must match configuration.id."
            )
        collection_providers.AccountProvider.instance().update_exchange_config(
            self._user_id,
            edit_payload.configuration,
        )
        self._mark_user_action_completed(user_action)
