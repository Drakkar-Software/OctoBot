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

import datetime

import octobot.community.account_backend.errors as account_backend_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.user_actions.user_actions_executor.base_user_action_executor as user_actions_executor_base

_FAILURE_ERROR_DETAILS_MAX_LENGTH = 8_000


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class AccountUserActionExecutor(user_actions_executor_base.UserActionExecutor):
    """Executes user actions whose ``UserAction.result`` oneOf uses ``AccountActionResult``."""

    def _build_failure_user_action_result(
        self,
        user_action: protocol_models.UserAction,
        exc: BaseException,
    ) -> protocol_models.UserActionResult:
        now = _utc_now()
        return protocol_models.UserActionResult(
            actual_instance=protocol_models.AccountActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.ACCOUNT,
                error_message=self._get_error_message(exc),
                error_details=str(exc)[:_FAILURE_ERROR_DETAILS_MAX_LENGTH],
            )
        )

    def _get_error_message(self, exc: BaseException) -> protocol_models.AccountActionResultErrorMessage:
        if isinstance(exc, (node_errors.AccountNotFoundError, account_backend_errors.AccountNotFoundError)):
            return protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND
        if isinstance(
            exc,
            (
                node_errors.InvalidUserActionPayloadError,
                node_errors.AccountContextMissingError,
                node_errors.UnsupportedUserActionConfigurationTypeError,
                account_backend_errors.DuplicateAccountError,
            ),
        ):
            return protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION
        return protocol_models.AccountActionResultErrorMessage(super()._get_error_message(exc))

    def _mark_user_action_completed(self, user_action: protocol_models.UserAction) -> None:
        now = _utc_now()
        user_action.status = protocol_models.UserActionStatus.COMPLETED
        user_action.result = protocol_models.UserActionResult(
            actual_instance=protocol_models.AccountActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.ACCOUNT,
            )
        )
