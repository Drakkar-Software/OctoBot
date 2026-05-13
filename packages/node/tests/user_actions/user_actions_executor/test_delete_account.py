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

import octobot.community.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.user_actions.user_actions_executor.delete_account as delete_account_executor

from . import account_executor_test_utils
from . import provider_assertions


class TestDeleteAccountActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_delete_with_wallet_and_id(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="del-1",
        )
        user_action = protocol_models.UserAction(id="ua-del", configuration=account_executor_test_utils.wrap_configuration(inner))
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot.community.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = delete_account_executor.DeleteAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            await executor.execute(user_action)
        provider_mock.delete_item.assert_called_once_with(account_executor_test_utils.WALLET_ADDRESS, "del-1")
        provider_assertions.assert_provider_user_action_terminal_state(
            user_action_id="ua-del",
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_wrong(self):
        inner = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=account_executor_test_utils.minimal_exchange_account(account_id="a"),
        )
        user_action = protocol_models.UserAction(id="ua-wrong-del", configuration=account_executor_test_utils.wrap_configuration(inner))
        executor = delete_account_executor.DeleteAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="DeleteAccountConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_provider_user_action_terminal_state(
            user_action_id="ua-wrong-del",
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_account_not_found_error_propagates(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="missing",
        )
        user_action = protocol_models.UserAction(id="ua-missing", configuration=account_executor_test_utils.wrap_configuration(inner))
        provider_mock = mock.Mock()
        provider_mock.delete_item.side_effect = collection_errors.ItemNotFoundError("missing")
        with mock.patch(
            "octobot.community.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = delete_account_executor.DeleteAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_provider_user_action_terminal_state(
            user_action_id="ua-missing",
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND,
        )
