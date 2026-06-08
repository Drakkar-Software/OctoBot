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

import typing

import octobot_commons.constants as commons_constants
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_node.scheduler.api as scheduler_api
import octobot_node.protocol.accounts as accounts_protocol
import octobot_node.protocol.strategies as strategies_protocol
import octobot_node.protocol.accounts_trading as accounts_trading_protocol


_AUTH_DETAIL_FIELD_NAMES = (
    "api_key",
    "api_secret",
    "api_password",
    "access_token",
    "encrypted",
)


def _auth_details_dict_has_credentials(auth_details: dict) -> bool:
    return bool(
        auth_details.get("api_key")
        or auth_details.get("api_secret")
        or auth_details.get("api_password")
        or auth_details.get("access_token")
        or auth_details.get("encrypted")
    )


def _redact_auth_details_dict(auth_details: dict) -> dict:
    redacted_auth_details = dict(auth_details)
    for field_name in _AUTH_DETAIL_FIELD_NAMES:
        if redacted_auth_details.get(field_name):
            redacted_auth_details[field_name] = commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
    return redacted_auth_details


def _redact_action_for_debug(action: protocol_models.Action) -> protocol_models.Action:
    if action.action_type != flow_enums.ActionType.APPLY_CONFIGURATION.value:
        return action
    configuration = action.configuration
    if configuration is None:
        return action
    exchange_account_details = configuration.get("exchange_account_details")
    if not isinstance(exchange_account_details, dict):
        return action
    auth_details = exchange_account_details.get("auth_details")
    if not isinstance(auth_details, dict) or not _auth_details_dict_has_credentials(auth_details):
        return action
    redacted_configuration = {
        **configuration,
        "exchange_account_details": {
            **exchange_account_details,
            "auth_details": _redact_auth_details_dict(auth_details),
        },
    }
    return action.model_copy(update={"configuration": redacted_configuration})


def _redact_actions_for_debug(
    actions: typing.Optional[list[protocol_models.Action]],
) -> typing.Optional[list[protocol_models.Action]]:
    if actions is None:
        return None
    return [_redact_action_for_debug(action) for action in actions]


def _automation_state_for_debug(
    automation: protocol_models.AutomationState,
) -> protocol_models.AutomationState:
    return automation.model_copy(
        update={
            "actions": _redact_actions_for_debug(automation.actions),
            "priority_actions": _redact_actions_for_debug(automation.priority_actions),
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


async def get_debug_state(wallet_address: str) -> protocol_models.DebugState:
    automations = [
        _automation_state_for_debug(automation)
        for automation in await scheduler_api.get_automation_states(wallet_address)
    ]
    user_actions = await scheduler_api.list_user_actions(wallet_address, active_only=False)
    account_state = accounts_protocol.get_accounts_state(wallet_address)
    strategies_state = strategies_protocol.get_strategies_state(wallet_address)
    bound_account_ids = _account_ids_bound_to_running_automations(automations)
    account_tradings = accounts_trading_protocol.get_account_trading_summaries(
        wallet_address,
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
