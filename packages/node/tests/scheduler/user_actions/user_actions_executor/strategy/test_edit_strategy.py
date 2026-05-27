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

from . import strategy_executor_test_utils
from .. import provider_assertions

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.strategy.edit_strategy as edit_strategy_executor


class TestEditStrategyActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_update_with_wallet_and_strategy(self):
        strategy_model = strategy_executor_test_utils.minimal_strategy(
            strategy_id="edit-strategy",
            name="Updated name",
        )
        inner = protocol_models.EditStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="edit-strategy",
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-edit-strategy",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot_sync.sync.collection_providers.StrategyProvider.instance",
            return_value=provider_mock,
        ):
            executor = edit_strategy_executor.EditStrategyActionExecutor(
                strategy_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.update_item.assert_called_once_with(
            strategy_executor_test_utils.WALLET_ADDRESS,
            strategy_model,
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="strategy",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_configuration_is_none(self):
        inner = protocol_models.EditStrategyConfiguration.model_construct(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="edit-strategy",
            configuration=None,
        )
        user_action = protocol_models.UserAction(
            id="ua-edit-none",
            configuration=protocol_models.UserActionConfiguration.model_construct(
                actual_instance=inner,
            ),
        )
        executor = edit_strategy_executor.EditStrategyActionExecutor(
            strategy_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="configuration is required"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_outer_id_mismatches_configuration_id(self):
        strategy_model = strategy_executor_test_utils.minimal_strategy(strategy_id="inner-id")
        inner = protocol_models.EditStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="outer-id",
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-mismatch",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        executor = edit_strategy_executor.EditStrategyActionExecutor(
            strategy_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="must match configuration.id"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_wrong(self):
        inner = protocol_models.CreateStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_CREATE,
            configuration=strategy_executor_test_utils.minimal_strategy(strategy_id="cfg"),
        )
        user_action = protocol_models.UserAction(
            id="ua-wrong-edit",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        executor = edit_strategy_executor.EditStrategyActionExecutor(
            strategy_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="EditStrategyConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_strategy_not_found_error_propagates(self):
        strategy_model = strategy_executor_test_utils.minimal_strategy(strategy_id="missing-strategy")
        inner = protocol_models.EditStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="missing-strategy",
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-missing",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.update_item.side_effect = collection_errors.ItemNotFoundError("missing-strategy")
        with mock.patch(
            "octobot_sync.sync.collection_providers.StrategyProvider.instance",
            return_value=provider_mock,
        ):
            executor = edit_strategy_executor.EditStrategyActionExecutor(
                strategy_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.STRATEGY_NOT_FOUND,
        )
