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

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.base_user_action_executor as user_actions_executor_base
import octobot_node.constants as constants


class AutomationUserActionExecutor(user_actions_executor_base.UserActionExecutor):
    """Executes user actions whose ``UserAction.result`` oneOf uses ``AutomationActionResult``."""

    def _build_failure_user_action_result(
        self,
        user_action: protocol_models.UserAction,
        exc: BaseException,
    ) -> protocol_models.UserActionResult:
        now = timestamp_util.utc_now_datetime()
        return protocol_models.UserActionResult(
            actual_instance=protocol_models.AutomationActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.AUTOMATION,
                error_message=self._get_error_message(exc),
                error_details=str(exc)[:constants.FAILURE_ERROR_DETAILS_MAX_LENGTH],
            )
        )

    def _get_error_message(self, exc: BaseException) -> protocol_models.AutomationActionResultErrorMessage:
        if isinstance(exc, (
            node_errors.ActiveAutomationWorkflowNotFoundError,
            node_errors.AmbiguousActiveAutomationWorkflowError
        )):
            return protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND
        if isinstance(exc, node_errors.AccountNotFoundError):
            return protocol_models.AutomationActionResultErrorMessage.ACCOUNT_NOT_FOUND
        if isinstance(exc, node_errors.AccountAuthenticationNotFoundError):
            return protocol_models.AutomationActionResultErrorMessage.ACCOUNT_AUTHENTICATION_DETAILS_NOT_FOUND
        if isinstance(exc, node_errors.AutomationStrategyNotFoundError):
            return protocol_models.AutomationActionResultErrorMessage.STRATEGY_NOT_FOUND
        if isinstance(exc, node_errors.AutomationStrategyVersionMismatchError):
            return protocol_models.AutomationActionResultErrorMessage.STRATEGY_VERSION_NOT_FOUND
        if isinstance(exc, node_errors.UnknownTradingTypeError):
            return protocol_models.AutomationActionResultErrorMessage.UNKNOWN_TRADING_TYPE
        if isinstance(exc, node_errors.AmbiguousTradingTypeError):
            return protocol_models.AutomationActionResultErrorMessage.AMBIGUOUS_TRADING_TYPE
        if isinstance(exc, node_errors.AmbiguousExchangeConfigError):
            return protocol_models.AutomationActionResultErrorMessage.AMBIGUOUS_EXCHANGE_CONFIG
        if isinstance(
            exc,
            (
                node_errors.InvalidUserActionPayloadError,
                node_errors.InvalidAutomationConfigurationError,
                node_errors.UnsupportedAutomationConfigurationTypeError,
                node_errors.UnsupportedUserActionConfigurationTypeError,
            ),
        ):
            return protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION
        return protocol_models.AutomationActionResultErrorMessage(super()._get_error_message(exc))

    def _mark_user_action_completed(
        self,
        user_action: protocol_models.UserAction,
        *,
        created_automation_id: typing.Optional[str] = None,
    ) -> None:
        now = timestamp_util.utc_now_datetime()
        user_action.status = protocol_models.UserActionStatus.COMPLETED
        user_action.result = protocol_models.UserActionResult(
            actual_instance=protocol_models.AutomationActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.AUTOMATION,
                created_automation_id=created_automation_id,
            )
        )
