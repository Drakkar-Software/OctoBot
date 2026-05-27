#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime
import typing

import octobot_node.constants as octobot_node_constants
import octobot_protocol.models as protocol_models


def resolve_user_action_result_type(
    user_action: protocol_models.UserAction,
) -> protocol_models.UserActionResultType:
    configuration = user_action.configuration
    if configuration is None or configuration.actual_instance is None:
        return protocol_models.UserActionResultType.ACCOUNT
    action_type = configuration.actual_instance.action_type
    match action_type:
        case (
            protocol_models.UserActionType.AUTOMATION_CREATE
            | protocol_models.UserActionType.AUTOMATION_EDIT
            | protocol_models.UserActionType.AUTOMATION_STOP
            | protocol_models.UserActionType.AUTOMATION_SIGNAL
        ):
            return protocol_models.UserActionResultType.AUTOMATION
        case (
            protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE
            | protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT
            | protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE
        ):
            return protocol_models.UserActionResultType.EXCHANGE_CONFIG
        case (
            protocol_models.UserActionType.STRATEGY_CREATE
            | protocol_models.UserActionType.STRATEGY_EDIT
            | protocol_models.UserActionType.STRATEGY_DELETE
        ):
            return protocol_models.UserActionResultType.STRATEGY
        case (
            protocol_models.UserActionType.ACCOUNT_CREATE
            | protocol_models.UserActionType.ACCOUNT_EDIT
            | protocol_models.UserActionType.ACCOUNT_DELETE
            | protocol_models.UserActionType.ACCOUNTS_REFRESH
        ):
            return protocol_models.UserActionResultType.ACCOUNT
        case (
            protocol_models.UserActionType.ACCOUNT_AUTH_CREATE
            | protocol_models.UserActionType.ACCOUNT_AUTH_EDIT
            | protocol_models.UserActionType.ACCOUNT_AUTH_DELETE
        ):
            return protocol_models.UserActionResultType.ACCOUNT_AUTH
        case _:
            raise ValueError(f"Unknown user action type: {action_type}")


def build_synthesized_failure_user_action_result(
    *,
    result_type: protocol_models.UserActionResultType,
    updated_at: datetime.datetime,
    error_details: str,
) -> protocol_models.UserActionResult:
    match result_type:
        case protocol_models.UserActionResultType.AUTOMATION:
            return protocol_models.UserActionResult(
                actual_instance=protocol_models.AutomationActionResult(
                    updated_at=updated_at,
                    result_type=result_type,
                    error_message=protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR,
                    error_details=error_details,
                )
            )
        case protocol_models.UserActionResultType.EXCHANGE_CONFIG:
            return protocol_models.UserActionResult(
                actual_instance=protocol_models.ExchangeConfigActionResult(
                    updated_at=updated_at,
                    result_type=result_type,
                    error_message=protocol_models.ExchangeConfigActionResultErrorMessage.INTERNAL_ERROR,
                    error_details=error_details,
                )
            )
        case protocol_models.UserActionResultType.STRATEGY:
            return protocol_models.UserActionResult(
                actual_instance=protocol_models.StrategyActionResult(
                    updated_at=updated_at,
                    result_type=result_type,
                    error_message=protocol_models.StrategyActionResultErrorMessage.INTERNAL_ERROR,
                    error_details=error_details,
                )
            )
        case protocol_models.UserActionResultType.ACCOUNT_AUTH:
            return protocol_models.UserActionResult(
                actual_instance=protocol_models.AccountAuthActionResult(
                    updated_at=updated_at,
                    result_type=result_type,
                    error_message=protocol_models.AccountAuthActionResultErrorMessage.INTERNAL_ERROR,
                    error_details=error_details,
                )
            )
        case _:
            return protocol_models.UserActionResult(
                actual_instance=protocol_models.AccountActionResult(
                    updated_at=updated_at,
                    result_type=protocol_models.UserActionResultType.ACCOUNT,
                    error_message=protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR,
                    error_details=error_details,
                )
            )


def build_minimal_user_action_for_workflow(
    *,
    workflow_id: str,
    terminal: bool,
    updated_at: datetime.datetime,
    parse_error: str,
    partial_user_action_id: typing.Optional[str] = None,
    workflow_error: typing.Optional[str] = None,
) -> protocol_models.UserAction:
    user_action_id = partial_user_action_id or workflow_id
    error_details = parse_error
    if workflow_error:
        error_details = f"{parse_error}: {workflow_error}"
    error_details = error_details[:octobot_node_constants.FAILURE_ERROR_DETAILS_MAX_LENGTH]
    if terminal:
        return protocol_models.UserAction(
            id=user_action_id,
            status=protocol_models.UserActionStatus.FAILED,
            updated_at=updated_at,
            result=build_synthesized_failure_user_action_result(
                result_type=protocol_models.UserActionResultType.ACCOUNT,
                updated_at=updated_at,
                error_details=error_details,
            ),
        )
    return protocol_models.UserAction(
        id=user_action_id,
        status=protocol_models.UserActionStatus.PENDING,
        updated_at=updated_at,
    )
