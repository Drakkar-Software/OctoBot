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
import octobot_node.scheduler.user_actions.user_actions_executor.refresh_accounts as refresh_accounts_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module

from . import account_executor_test_utils
from . import provider_assertions


class TestRefreshAccountsActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_updates_all_accounts_when_ids_are_not_provided(self):
        first_account = account_executor_test_utils.minimal_exchange_account(account_id="acc-1")
        second_account = account_executor_test_utils.minimal_exchange_account(account_id="acc-2")
        checked_first_account = first_account.model_copy(
            update={
                "state": protocol_models.AccountState(
                    status=protocol_models.AccountStatus.VALID,
                    message=protocol_models.AccountStatusMessage.VALID,
                )
            }
        )
        checked_second_account = second_account.model_copy(
            update={
                "state": protocol_models.AccountState(
                    status=protocol_models.AccountStatus.INVALID,
                    message=protocol_models.AccountStatusMessage.INVALID_API_KEYS,
                )
            }
        )
        refresh_inner = protocol_models.RefreshAccountsConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
        )
        user_action = protocol_models.UserAction(id="ua-refresh-all", configuration=account_executor_test_utils.wrap_configuration(refresh_inner))
        provider_mock = mock.Mock()
        provider_mock.list_items.return_value = [first_account, second_account]
        provider_mock.get_item.side_effect = [first_account, second_account]
        with (
            mock.patch(
                "octobot.community.collection_providers.AccountProvider.instance",
                return_value=provider_mock,
            ),
            mock.patch.object(
                account_state_updater_module,
                "update_account_state",
                new=mock.AsyncMock(side_effect=[checked_first_account, checked_second_account]),
            ) as check_mock,
        ):
            executor = refresh_accounts_executor.RefreshAccountsActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            await executor.execute(user_action)
        provider_mock.list_items.assert_called_once_with(account_executor_test_utils.WALLET_ADDRESS)
        assert provider_mock.get_item.call_count == 2
        provider_mock.update_item.assert_has_calls(
            [
                mock.call(account_executor_test_utils.WALLET_ADDRESS, checked_first_account),
                mock.call(account_executor_test_utils.WALLET_ADDRESS, checked_second_account),
            ]
        )
        assert check_mock.await_count == 2
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_updates_only_requested_accounts(self):
        account_model = account_executor_test_utils.minimal_exchange_account(account_id="acc-1")
        checked_account = account_model.model_copy(
            update={
                "state": protocol_models.AccountState(
                    status=protocol_models.AccountStatus.VALID,
                    message=protocol_models.AccountStatusMessage.VALID,
                )
            }
        )
        refresh_inner = protocol_models.RefreshAccountsConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
            account_ids=["acc-1"],
        )
        user_action = protocol_models.UserAction(id="ua-refresh-one", configuration=account_executor_test_utils.wrap_configuration(refresh_inner))
        provider_mock = mock.Mock()
        provider_mock.get_item.return_value = account_model
        with (
            mock.patch(
                "octobot.community.collection_providers.AccountProvider.instance",
                return_value=provider_mock,
            ),
            mock.patch.object(
                account_state_updater_module,
                "update_account_state",
                new=mock.AsyncMock(return_value=checked_account),
            ),
        ):
            executor = refresh_accounts_executor.RefreshAccountsActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            await executor.execute(user_action)
        provider_mock.list_items.assert_not_called()
        provider_mock.get_item.assert_called_once_with(account_executor_test_utils.WALLET_ADDRESS, "acc-1")
        provider_mock.update_item.assert_called_once_with(account_executor_test_utils.WALLET_ADDRESS, checked_account)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_is_wrong(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="acc-1",
        )
        user_action = protocol_models.UserAction(id="ua-refresh-wrong", configuration=account_executor_test_utils.wrap_configuration(inner))
        executor = refresh_accounts_executor.RefreshAccountsActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="RefreshAccountsConfiguration"):
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
        blockchain_account = account_executor_test_utils.minimal_blockchain_account(account_id="acc-blockchain")
        refresh_inner = protocol_models.RefreshAccountsConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
            account_ids=["acc-blockchain"],
        )
        user_action = protocol_models.UserAction(id="ua-refresh-blockchain", configuration=account_executor_test_utils.wrap_configuration(refresh_inner))
        provider_mock = mock.Mock()
        provider_mock.get_item.return_value = blockchain_account
        with mock.patch(
            "octobot.community.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = refresh_accounts_executor.RefreshAccountsActionExecutor(account_executor_test_utils.WALLET_ADDRESS)
            with pytest.raises(node_errors.InvalidUserActionPayloadError, match="Blockchain accounts are not supported yet"):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )
