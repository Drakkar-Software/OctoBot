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
import octobot_node.scheduler.user_actions.user_actions_executor.account.account_user_action_executor as account_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater


def _get_edit_account_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.EditAccountConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete edit-account configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.EditAccountConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"EditAccountActionExecutor expected EditAccountConfiguration, got {type(payload).__name__}"
        )
    return payload


class EditAccountActionExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        edit_payload = _get_edit_account_payload(user_action)
        if edit_payload.configuration is None:
            raise node_errors.InvalidUserActionPayloadError(
                "EditAccountConfiguration.configuration is required to update an account."
            )
        if edit_payload.configuration.id != edit_payload.id:
            raise node_errors.InvalidUserActionPayloadError(
                "EditAccountConfiguration.id must match configuration.id."
            )
        checked_account = await account_state_updater.update_account_state(
            edit_payload.configuration,
            self._user_id,
        )
        collection_providers.AccountProvider.instance().update_item(
            self._user_id,
            checked_account,
        )
        self._mark_user_action_completed(user_action)
