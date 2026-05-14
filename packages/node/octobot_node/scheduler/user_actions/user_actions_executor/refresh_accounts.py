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

import octobot.community.collection_providers as collection_providers
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.account_user_action_executor as account_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater


def _get_refresh_accounts_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.RefreshAccountsConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete refresh-accounts configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.RefreshAccountsConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"RefreshAccountsActionExecutor expected RefreshAccountsConfiguration, got {type(payload).__name__}"
        )
    return payload


class RefreshAccountsActionExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        refresh_payload = _get_refresh_accounts_payload(user_action)
        account_provider = collection_providers.AccountProvider.instance()
        account_ids_to_refresh = refresh_payload.account_ids or [
            account.id for account in account_provider.list_items(self._wallet_address)
        ]
        for account_id in account_ids_to_refresh:
            account = account_provider.get_item(self._wallet_address, account_id)
            checked_account = await account_state_updater.update_account_state(account)
            account_provider.update_item(self._wallet_address, checked_account)
        self._mark_user_action_completed(user_action)
