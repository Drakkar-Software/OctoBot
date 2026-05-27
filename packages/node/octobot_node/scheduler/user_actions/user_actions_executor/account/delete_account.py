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


def _get_delete_account_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.DeleteAccountConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete delete-account configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.DeleteAccountConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"DeleteAccountActionExecutor expected DeleteAccountConfiguration, got {type(payload).__name__}"
        )
    return payload


class DeleteAccountActionExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        delete_payload = _get_delete_account_payload(user_action)
        collection_providers.AccountProvider.instance().delete_item(
            self._wallet_address,
            delete_payload.id,
        )
        self._mark_user_action_completed(user_action)
