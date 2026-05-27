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

import octobot_commons.timestamp_util as timestamp_util
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.base_user_action_executor as user_actions_executor_base
import octobot_node.constants as constants


def with_updated_at(
    authentication: protocol_models.AccountAuthentication,
) -> protocol_models.AccountAuthentication:
    return authentication.model_copy(
        update={"updated_at": timestamp_util.utc_now_datetime()},
    )


class AccountAuthUserActionExecutor(user_actions_executor_base.UserActionExecutor):
    """Executes user actions whose ``UserAction.result`` oneOf uses ``AccountAuthActionResult``."""

    def _build_failure_user_action_result(
        self,
        user_action: protocol_models.UserAction,
        exc: BaseException,
    ) -> protocol_models.UserActionResult:
        now = timestamp_util.utc_now_datetime()
        return protocol_models.UserActionResult(
            actual_instance=protocol_models.AccountAuthActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.ACCOUNT_AUTH,
                error_message=self._get_error_message(exc),
                error_details=str(exc)[:constants.FAILURE_ERROR_DETAILS_MAX_LENGTH],
            )
        )

    def _get_error_message(
        self,
        exc: BaseException,
    ) -> protocol_models.AccountAuthActionResultErrorMessage:
        if isinstance(exc, collection_errors.ItemNotFoundError):
            return protocol_models.AccountAuthActionResultErrorMessage.ACCOUNT_AUTH_NOT_FOUND
        if isinstance(exc, collection_errors.DuplicateItemError):
            return protocol_models.AccountAuthActionResultErrorMessage.DUPLICATE_ITEM
        if isinstance(
            exc,
            (
                node_errors.InvalidUserActionPayloadError,
                node_errors.UnsupportedUserActionConfigurationTypeError,
            ),
        ):
            return protocol_models.AccountAuthActionResultErrorMessage.INVALID_CONFIGURATION
        return protocol_models.AccountAuthActionResultErrorMessage(super()._get_error_message(exc))

    def _mark_user_action_completed(self, user_action: protocol_models.UserAction) -> None:
        now = timestamp_util.utc_now_datetime()
        user_action.status = protocol_models.UserActionStatus.COMPLETED
        user_action.result = protocol_models.UserActionResult(
            actual_instance=protocol_models.AccountAuthActionResult(
                updated_at=now,
                result_type=protocol_models.UserActionResultType.ACCOUNT_AUTH,
            )
        )
