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


def _wallet_account_ids(
    accounts: list[protocol_models.Account] | None,
) -> list[str]:
    if not accounts:
        return []
    return [
        account.id
        for account in accounts
        if account.id
    ]


async def get_debug_state(user_id: str) -> protocol_models.DebugState:
    automations = await scheduler_api.get_automation_states(user_id)
    user_actions = await scheduler_api.list_user_actions(user_id, active_only=False)
    account_state = accounts_protocol.get_accounts_state(user_id)
    strategies_state = strategies_protocol.get_strategies_state(user_id)
    account_tradings = accounts_trading_protocol.get_account_trading_summaries(
        user_id,
        _wallet_account_ids(account_state.accounts),
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
