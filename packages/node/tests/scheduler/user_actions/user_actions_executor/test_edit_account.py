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

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.edit_account as edit_account_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module

from . import account_executor_test_utils
from . import provider_assertions


class TestEditAccountActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_update_with_wallet_and_account(self):
        account_model = account_executor_test_utils.minimal_exchange_account(account_id="edit-acc")
        inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="edit-acc",
            configuration=account_model,
        )
        user_action = protocol_models.UserAction(id="ua-edit", configuration=account_executor_test_utils.wrap_configuration(inner))
        provider_mock = mock.Mock()
        with (
            mock.patch(
                "octobot.community.collection_providers.AccountProvider.instance",
                return_value=provider_mock,
            ),
            mock.patch.object(
                account_state_updater_module,
                "update_account_state",
                new=mock.AsyncMock(return_value=account_model),
            ),
        ):
            executor = edit_account_executor.EditAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            await executor.execute(user_action)
        provider_mock.update_item.assert_called_once_with(account_executor_test_utils.WALLET_ADDRESS, account_model)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_configuration_is_none(self):
        inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="edit-acc",
            configuration=None,
        )
        user_action = protocol_models.UserAction(id="ua-edit-none", configuration=account_executor_test_utils.wrap_configuration(inner))
        executor = edit_account_executor.EditAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="configuration is required"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_outer_id_mismatches_configuration_id(self):
        account_model = account_executor_test_utils.minimal_exchange_account(account_id="inner-id")
        inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="outer-id",
            configuration=account_model,
        )
        user_action = protocol_models.UserAction(id="ua-mismatch", configuration=account_executor_test_utils.wrap_configuration(inner))
        executor = edit_account_executor.EditAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="must match configuration.id"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_for_unsupported_blockchain_account(self):
        account_model = account_executor_test_utils.minimal_blockchain_account(account_id="edit-blockchain")
        inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="edit-blockchain",
            configuration=account_model,
        )
        user_action = protocol_models.UserAction(id="ua-edit-blockchain", configuration=account_executor_test_utils.wrap_configuration(inner))
        executor = edit_account_executor.EditAccountActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="Blockchain accounts are not supported yet"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )
