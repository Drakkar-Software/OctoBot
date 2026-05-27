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
import octobot_node.scheduler.user_actions.user_actions_executor.strategy.create_strategy as create_strategy_executor


class TestCreateStrategyActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_create_with_wallet_and_strategy(self):
        strategy_model = strategy_executor_test_utils.minimal_strategy(strategy_id="new-strategy")
        inner = protocol_models.CreateStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_CREATE,
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-create-strategy",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot_sync.sync.collection_providers.StrategyProvider.instance",
            return_value=provider_mock,
        ):
            executor = create_strategy_executor.CreateStrategyActionExecutor(
                strategy_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.create_item.assert_called_once_with(
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
    async def test_raises_when_configuration_missing(self):
        user_action = protocol_models.UserAction(id="ua-bad", configuration=None)
        executor = create_strategy_executor.CreateStrategyActionExecutor(
            strategy_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="create-strategy configuration"):
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
        inner = protocol_models.DeleteStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_DELETE,
            id="x",
        )
        user_action = protocol_models.UserAction(
            id="ua-wrong",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        executor = create_strategy_executor.CreateStrategyActionExecutor(
            strategy_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="CreateStrategyConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_duplicate_strategy_error_propagates(self):
        strategy_model = strategy_executor_test_utils.minimal_strategy(strategy_id="dup-strategy")
        inner = protocol_models.CreateStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_CREATE,
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-dup",
            configuration=strategy_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.create_item.side_effect = collection_errors.DuplicateItemError("dup-strategy")
        with mock.patch(
            "octobot_sync.sync.collection_providers.StrategyProvider.instance",
            return_value=provider_mock,
        ):
            executor = create_strategy_executor.CreateStrategyActionExecutor(
                strategy_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.DuplicateItemError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="strategy",
            expect_error_details=True,
            expected_error_message=protocol_models.StrategyActionResultErrorMessage.DUPLICATE_ITEM,
        )
