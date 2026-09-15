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
import octobot_sync.sync.collection_backend.errors as collection_errors

from .account import account_executor_test_utils
from . import provider_assertions

import octobot_node.errors as node_errors

import octobot_node.scheduler.user_actions.user_actions_executor.account.reset_account_trading_data as reset_account_trading_data_executor


class TestResetAccountTradingDataActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_clears_trading_data_and_completes(self):
        reset_inner = protocol_models.ResetAccountTradingDataConfiguration(
            action_type=protocol_models.UserActionType.RESET_ACCOUNT_TRADING_DATA,
            account_ids=["acc-owned"],
        )
        user_action = protocol_models.UserAction(
            id="ua-reset-account-trading",
            configuration=account_executor_test_utils.wrap_configuration(reset_inner),
        )
        owned_account = account_executor_test_utils.minimal_exchange_account(account_id="acc-owned")
        account_provider_mock = mock.Mock()
        account_provider_mock.get_item.return_value = owned_account
        with (
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=account_provider_mock,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.account.reset_account_trading_data.accounts_trading_module.reset_account_trading_data",
            ) as reset_mock,
        ):
            executor = reset_account_trading_data_executor.ResetAccountTradingDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        account_provider_mock.get_item.assert_called_once_with(
            account_executor_test_utils.WALLET_ADDRESS,
            "acc-owned",
        )
        reset_mock.assert_called_once_with(
            account_executor_test_utils.WALLET_ADDRESS,
            "acc-owned",
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_account_id_not_owned(self):
        reset_inner = protocol_models.ResetAccountTradingDataConfiguration(
            action_type=protocol_models.UserActionType.RESET_ACCOUNT_TRADING_DATA,
            account_ids=["foreign-acc"],
        )
        user_action = protocol_models.UserAction(
            id="ua-reset-account-trading-foreign",
            configuration=account_executor_test_utils.wrap_configuration(reset_inner),
        )
        account_provider_mock = mock.Mock()
        account_provider_mock.get_item.side_effect = collection_errors.ItemNotFoundError("missing")
        with (
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=account_provider_mock,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.account.reset_account_trading_data.accounts_trading_module.reset_account_trading_data",
            ) as reset_mock,
        ):
            executor = reset_account_trading_data_executor.ResetAccountTradingDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        reset_mock.assert_not_called()
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_raises_when_account_ids_empty(self):
        reset_inner = protocol_models.ResetAccountTradingDataConfiguration.model_construct(
            action_type=protocol_models.UserActionType.RESET_ACCOUNT_TRADING_DATA,
            account_ids=[],
        )
        user_action = protocol_models.UserAction(
            id="ua-reset-account-trading-empty",
            configuration=protocol_models.UserActionConfiguration.model_construct(
                actual_instance=reset_inner,
            ),
        )
        executor = reset_account_trading_data_executor.ResetAccountTradingDataActionExecutor(
            account_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="at least one account id"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_is_wrong(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="acc-1",
        )
        user_action = protocol_models.UserAction(
            id="ua-reset-account-trading-wrong",
            configuration=account_executor_test_utils.wrap_configuration(inner),
        )
        executor = reset_account_trading_data_executor.ResetAccountTradingDataActionExecutor(
            account_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="ResetAccountTradingDataConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )
