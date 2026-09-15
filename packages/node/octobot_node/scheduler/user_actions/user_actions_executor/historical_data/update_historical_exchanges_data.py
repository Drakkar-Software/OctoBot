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
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.errors as node_errors
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.workflows.params as workflow_params_module
import octobot_node.scheduler.user_actions.user_actions_executor.account.account_user_action_executor as account_user_action_executor


def _get_update_historical_exchanges_data_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.UpdateHistoricalExchangesDataConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete update-historical-exchanges-data configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.UpdateHistoricalExchangesDataConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            "UpdateHistoricalExchangesDataActionExecutor expected "
            f"UpdateHistoricalExchangesDataConfiguration, got {type(payload).__name__}"
        )
    return payload


class UpdateHistoricalExchangesDataActionExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        payload = _get_update_historical_exchanges_data_payload(user_action)
        if not scheduler_module.is_initialized():
            raise RuntimeError("Scheduler is not initialized")
        account_provider = collection_providers.AccountProvider.instance()
        # Client-supplied account_ids are scoped to this wallet only: get_item raises
        # if an id does not belong to self._user_id (same check as refresh_accounts).
        if payload.account_ids:
            for account_id in payload.account_ids:
                account_provider.get_item(self._user_id, account_id)
        self.post_actions.portfolio_history_collection_params = (
            workflow_params_module.PortfolioHistoryCollectionParams(
                wallet_ids=[self._user_id],
                account_ids=payload.account_ids,
            )
        )
        self._mark_user_action_completed(user_action)
