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

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.user_actions.user_actions_executor as user_actions_executor_package


async def execute_user_action(
    user_action: protocol_models.UserAction,
    wallet_address: str,
) -> None:
    if user_action.configuration is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration is required to execute a user action."
        )
    if user_action.configuration.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration.actual_instance is required to execute a user action."
        )
    user_action_executor = _get_user_action_executor(user_action.configuration)
    await user_action_executor(wallet_address).execute(user_action)


def _get_user_action_executor(
    configuration: protocol_models.UserActionConfiguration,
) -> typing.Type["user_actions_executor_package.UserActionExecutor"]:
    actual = configuration.actual_instance
    if actual is None:
        raise node_errors.InvalidUserActionPayloadError("UserActionConfiguration.actual_instance is required.")
    match type(actual):
        case protocol_models.CreateAutomationConfiguration:
            return user_actions_executor_package.CreateAutomationActionExecutor
        case protocol_models.EditAutomationConfiguration:
            return user_actions_executor_package.EditAutomationActionExecutor
        case protocol_models.StopAutomationConfiguration:
            return user_actions_executor_package.StopAutomationActionExecutor
        case protocol_models.CreateAccountConfiguration:
            return user_actions_executor_package.CreateAccountActionExecutor
        case protocol_models.EditAccountConfiguration:
            return user_actions_executor_package.EditAccountActionExecutor
        case protocol_models.DeleteAccountConfiguration:
            return user_actions_executor_package.DeleteAccountActionExecutor
        case protocol_models.RefreshAccountsConfiguration:
            return user_actions_executor_package.RefreshAccountsActionExecutor
        case _:
            raise node_errors.UnsupportedUserActionConfigurationTypeError(
                f"Unknown user action configuration type: {type(actual).__name__}"
            )
