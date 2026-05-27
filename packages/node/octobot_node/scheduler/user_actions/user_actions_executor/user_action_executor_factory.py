#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import typing

import octobot_protocol.models as protocol_models
import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor as user_actions_executor_package


def user_action_executor_factory(
    user_action: protocol_models.UserAction,
) -> typing.Type["user_actions_executor_package.UserActionExecutor"]:
    if user_action.configuration is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration is required to execute a user action."
        )
    if user_action.configuration.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration.actual_instance is required to execute a user action."
        )
    actual = user_action.configuration.actual_instance
    if actual is None:
        raise node_errors.InvalidUserActionPayloadError("UserActionConfiguration.actual_instance is required.")
    match type(actual):
        case protocol_models.CreateAutomationConfiguration:
            return user_actions_executor_package.CreateAutomationActionExecutor
        case protocol_models.EditAutomationConfiguration:
            return user_actions_executor_package.EditAutomationActionExecutor
        case protocol_models.StopAutomationConfiguration:
            return user_actions_executor_package.StopAutomationActionExecutor
        case protocol_models.SignalAutomationConfiguration:
            return user_actions_executor_package.SignalAutomationActionExecutor
        case protocol_models.CreateAccountConfiguration:
            return user_actions_executor_package.CreateAccountActionExecutor
        case protocol_models.EditAccountConfiguration:
            return user_actions_executor_package.EditAccountActionExecutor
        case protocol_models.DeleteAccountConfiguration:
            return user_actions_executor_package.DeleteAccountActionExecutor
        case protocol_models.RefreshAccountsConfiguration:
            return user_actions_executor_package.RefreshAccountsActionExecutor
        case protocol_models.CreateExchangeConfigConfiguration:
            return user_actions_executor_package.CreateExchangeConfigActionExecutor
        case protocol_models.EditExchangeConfigConfiguration:
            return user_actions_executor_package.EditExchangeConfigActionExecutor
        case protocol_models.DeleteExchangeConfigConfiguration:
            return user_actions_executor_package.DeleteExchangeConfigActionExecutor
        case protocol_models.CreateStrategyConfiguration:
            return user_actions_executor_package.CreateStrategyActionExecutor
        case protocol_models.EditStrategyConfiguration:
            return user_actions_executor_package.EditStrategyActionExecutor
        case protocol_models.DeleteStrategyConfiguration:
            return user_actions_executor_package.DeleteStrategyActionExecutor
        case protocol_models.CreateAccountAuthConfiguration:
            return user_actions_executor_package.CreateAccountAuthActionExecutor
        case protocol_models.EditAccountAuthConfiguration:
            return user_actions_executor_package.EditAccountAuthActionExecutor
        case protocol_models.DeleteAccountAuthConfiguration:
            return user_actions_executor_package.DeleteAccountAuthActionExecutor
        case _:
            raise node_errors.UnsupportedUserActionConfigurationTypeError(
                f"Unknown user action configuration type: {type(actual).__name__}"
            )
