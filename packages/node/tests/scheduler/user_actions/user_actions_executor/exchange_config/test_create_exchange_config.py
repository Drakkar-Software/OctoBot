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
import octobot_node.scheduler.user_actions.user_actions_executor.exchange_config.create_exchange_config as create_exchange_config_executor

from . import exchange_config_executor_test_utils
from .. import provider_assertions


class TestCreateExchangeConfigActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_create_with_wallet_and_exchange_config(self):
        exchange_config_model = exchange_config_executor_test_utils.minimal_exchange_config(
            config_id="new-config",
        )
        inner = protocol_models.CreateExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            configuration=exchange_config_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-create-config",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(
                exchange_config_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.create_exchange_config.assert_called_once_with(
            exchange_config_executor_test_utils.WALLET_ADDRESS,
            exchange_config_model,
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="exchange_config",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_raises_when_configuration_missing(self):
        user_action = protocol_models.UserAction(id="ua-bad", configuration=None)
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(
            exchange_config_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="create-exchange-config configuration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_wrong(self):
        inner = protocol_models.DeleteExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE,
            id="x",
        )
        user_action = protocol_models.UserAction(
            id="ua-wrong",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(
            exchange_config_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="CreateExchangeConfigConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_duplicate_exchange_config_error_propagates(self):
        exchange_config_model = exchange_config_executor_test_utils.minimal_exchange_config(
            config_id="dup-config",
        )
        inner = protocol_models.CreateExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            configuration=exchange_config_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-dup",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.create_exchange_config.side_effect = collection_errors.DuplicateItemError("dup-config")
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(
                exchange_config_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.DuplicateItemError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.DUPLICATE_ITEM,
        )
