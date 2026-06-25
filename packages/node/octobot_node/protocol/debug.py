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
import octobot_node.scheduler.api as scheduler_api
import octobot_node.protocol.accounts as accounts_protocol
import octobot_node.protocol.strategies as strategies_protocol
import octobot_node.protocol.accounts_trading as accounts_trading_protocol
import octobot_node.protocol.util.privacy_filter as privacy_filter


def _redact_user_actions_for_debug(
    user_actions: list[protocol_models.UserAction],
) -> list[protocol_models.UserAction]:
    return [
        privacy_filter.privatize_user_action(user_action)
        for user_action in user_actions
    ]


def _automation_state_for_debug(
    automation: protocol_models.AutomationState,
) -> protocol_models.AutomationState:
    return automation.model_copy(
        update={
            "actions": privacy_filter.privatize_dag_actions(automation.actions),
            "priority_actions": privacy_filter.privatize_dag_actions(
                automation.priority_actions,
            ),
        }
    )


def _account_ids_bound_to_running_automations(
    automations: list[protocol_models.AutomationState],
) -> list[str]:
    seen_account_ids: set[str] = set()
    bound_account_ids: list[str] = []
    for automation in automations:
        if automation.status != protocol_models.WorkflowStatus.RUNNING:
            continue
        if not automation.exchange_account_ids:
            continue
        for account_id in automation.exchange_account_ids:
            if account_id in seen_account_ids:
                continue
            seen_account_ids.add(account_id)
            bound_account_ids.append(account_id)
    return bound_account_ids


async def get_debug_state(user_id: str) -> protocol_models.DebugState:
    automations = [
        _automation_state_for_debug(automation)
        for automation in await scheduler_api.get_automation_states(user_id)
    ]
    user_actions = _redact_user_actions_for_debug(
        await scheduler_api.list_user_actions(user_id, active_only=False),
    )
    account_state = accounts_protocol.get_accounts_state(user_id)
    strategies_state = strategies_protocol.get_strategies_state(user_id)
    bound_account_ids = _account_ids_bound_to_running_automations(automations)
    account_tradings = accounts_trading_protocol.get_account_trading_summaries(
        user_id,
        bound_account_ids,
    )
    return protocol_models.DebugState(
        version=sync_constants.DEBUG_STATE_VERSION,
        debug=protocol_models.Debug(
            automations=automations,
            user_actions=user_actions,
            accounts=account_state.accounts,
            exchange_configs=account_state.exchange_configs,
            account_tradings=account_tradings,
            local_strategies=strategies_state.strategies,
        ),
    )
