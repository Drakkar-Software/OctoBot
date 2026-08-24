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

import octobot_node.scheduler.tasks as scheduler_tasks_module
import octobot_node.scheduler.user_actions.user_actions_executor.historical_data.update_historical_exchanges_data as update_historical_exchanges_data_executor
import octobot_node.scheduler.workflows.params as workflow_params_module
import octobot_node.scheduler.user_actions.user_action_post_actions as user_action_post_actions_module

from tests.scheduler import temp_dbos_scheduler


class TestUpdateHistoricalExchangesDataActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_sets_portfolio_history_collection_params_and_completes(self):
        update_inner = protocol_models.UpdateHistoricalExchangesDataConfiguration(
            action_type=protocol_models.UserActionType.UPDATE_HISTORICAL_EXCHANGES_DATA,
        )
        user_action = protocol_models.UserAction(
            id="ua-update-historical",
            configuration=account_executor_test_utils.wrap_configuration(update_inner),
        )
        with mock.patch(
            "octobot_node.scheduler.user_actions.user_actions_executor.historical_data.update_historical_exchanges_data.scheduler_module.is_initialized",
            return_value=True,
        ):
            executor = update_historical_exchanges_data_executor.UpdateHistoricalExchangesDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        collection_params = executor.post_actions.portfolio_history_collection_params
        assert collection_params is not None
        assert collection_params.wallet_ids == [account_executor_test_utils.WALLET_ADDRESS]
        assert collection_params.account_ids is None
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_validates_account_ids_belong_to_user(self):
        owned_account = account_executor_test_utils.minimal_exchange_account(account_id="acc-owned")
        update_inner = protocol_models.UpdateHistoricalExchangesDataConfiguration(
            action_type=protocol_models.UserActionType.UPDATE_HISTORICAL_EXCHANGES_DATA,
            account_ids=["acc-owned"],
        )
        user_action = protocol_models.UserAction(
            id="ua-update-historical-scoped",
            configuration=account_executor_test_utils.wrap_configuration(update_inner),
        )
        provider_mock = mock.Mock()
        provider_mock.get_item.return_value = owned_account
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.historical_data.update_historical_exchanges_data.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=provider_mock,
            ),
        ):
            executor = update_historical_exchanges_data_executor.UpdateHistoricalExchangesDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.get_item.assert_called_once_with(
            account_executor_test_utils.WALLET_ADDRESS,
            "acc-owned",
        )
        collection_params = executor.post_actions.portfolio_history_collection_params
        assert collection_params is not None
        assert collection_params.account_ids == ["acc-owned"]

    @pytest.mark.asyncio
    async def test_raises_when_account_id_not_owned(self):
        update_inner = protocol_models.UpdateHistoricalExchangesDataConfiguration(
            action_type=protocol_models.UserActionType.UPDATE_HISTORICAL_EXCHANGES_DATA,
            account_ids=["foreign-acc"],
        )
        user_action = protocol_models.UserAction(
            id="ua-update-historical-foreign",
            configuration=account_executor_test_utils.wrap_configuration(update_inner),
        )
        provider_mock = mock.Mock()
        provider_mock.get_item.side_effect = collection_errors.ItemNotFoundError("missing")
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.historical_data.update_historical_exchanges_data.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=provider_mock,
            ),
        ):
            executor = update_historical_exchanges_data_executor.UpdateHistoricalExchangesDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_raises_when_scheduler_not_initialized(self):
        update_inner = protocol_models.UpdateHistoricalExchangesDataConfiguration(
            action_type=protocol_models.UserActionType.UPDATE_HISTORICAL_EXCHANGES_DATA,
        )
        user_action = protocol_models.UserAction(
            id="ua-update-historical-no-scheduler",
            configuration=account_executor_test_utils.wrap_configuration(update_inner),
        )
        with mock.patch(
            "octobot_node.scheduler.user_actions.user_actions_executor.historical_data.update_historical_exchanges_data.scheduler_module.is_initialized",
            return_value=False,
        ):
            executor = update_historical_exchanges_data_executor.UpdateHistoricalExchangesDataActionExecutor(
                account_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_is_wrong(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="acc-1",
        )
        user_action = protocol_models.UserAction(
            id="ua-update-historical-wrong",
            configuration=account_executor_test_utils.wrap_configuration(inner),
        )
        executor = update_historical_exchanges_data_executor.UpdateHistoricalExchangesDataActionExecutor(
            account_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="UpdateHistoricalExchangesDataConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION,
        )


class TestUpdateHistoricalExchangesDataAfterUserActionExecution:
    @pytest.mark.asyncio
    async def test_triggers_portfolio_history_collection_when_post_action_set(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module

        trigger_mock = mock.AsyncMock(return_value="portfolio-history-workflow-id")
        collection_params = workflow_params_module.PortfolioHistoryCollectionParams(
            wallet_ids=["wallet-user-1"],
            account_ids=["acc-1"],
        )
        execution_result = workflow_params_module.UserActionExecutionResult(
            updated_user_action=protocol_models.UserAction(id="ua-update-historical"),
            post_actions=user_action_post_actions_module.UserActionPostActions(
                portfolio_history_collection_params=collection_params,
            ),
        )
        with mock.patch.object(
            scheduler_tasks_module,
            "trigger_portfolio_history_collection",
            trigger_mock,
        ):
            await user_action_workflow_module.UserActionWorkflow.after_user_action_execution(execution_result)
        trigger_mock.assert_awaited_once_with(collection_params)
