#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import mock
import pytest

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.account_auth.delete_account_auth as delete_account_auth_executor

from . import account_auth_executor_test_utils
from .. import provider_assertions


class TestDeleteAccountAuthActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_delete_with_wallet_and_id(self):
        inner = protocol_models.DeleteAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_DELETE,
            id="del-auth-1",
        )
        user_action = protocol_models.UserAction(
            id="ua-del-auth",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountAuthenticationProvider.instance",
            return_value=provider_mock,
        ):
            executor = delete_account_auth_executor.DeleteAccountAuthActionExecutor(
                account_auth_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.delete_item.assert_called_once_with(
            account_auth_executor_test_utils.WALLET_ADDRESS,
            "del-auth-1",
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account_auth",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_wrong(self):
        inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=account_auth_executor_test_utils.minimal_account_authentication(auth_id="auth"),
        )
        user_action = protocol_models.UserAction(
            id="ua-wrong-del",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        executor = delete_account_auth_executor.DeleteAccountAuthActionExecutor(
            account_auth_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="DeleteAccountAuthConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account_auth",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountAuthActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_account_auth_not_found_error_propagates(self):
        inner = protocol_models.DeleteAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_DELETE,
            id="missing-auth",
        )
        user_action = protocol_models.UserAction(
            id="ua-missing",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.delete_item.side_effect = collection_errors.ItemNotFoundError("missing-auth")
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountAuthenticationProvider.instance",
            return_value=provider_mock,
        ):
            executor = delete_account_auth_executor.DeleteAccountAuthActionExecutor(
                account_auth_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account_auth",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountAuthActionResultErrorMessage.ACCOUNT_AUTH_NOT_FOUND,
        )
