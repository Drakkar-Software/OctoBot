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
import octobot_node.scheduler.user_actions.user_actions_executor.exchange_config.edit_exchange_config as edit_exchange_config_executor

from . import exchange_config_executor_test_utils
from .. import provider_assertions


class TestEditExchangeConfigActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_update_with_wallet_and_exchange_config(self):
        exchange_config_model = exchange_config_executor_test_utils.minimal_exchange_config(
            config_id="edit-config",
            name="Updated name",
        )
        inner = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="edit-config",
            configuration=exchange_config_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-edit-config",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = edit_exchange_config_executor.EditExchangeConfigActionExecutor(
                exchange_config_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.update_exchange_config.assert_called_once_with(
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
    async def test_raises_when_configuration_is_none(self):
        inner = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="edit-config",
            configuration=None,
        )
        user_action = protocol_models.UserAction(
            id="ua-edit-none",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        executor = edit_exchange_config_executor.EditExchangeConfigActionExecutor(
            exchange_config_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="configuration is required"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_outer_id_mismatches_configuration_id(self):
        exchange_config_model = exchange_config_executor_test_utils.minimal_exchange_config(
            config_id="inner-id",
        )
        inner = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="outer-id",
            configuration=exchange_config_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-mismatch",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        executor = edit_exchange_config_executor.EditExchangeConfigActionExecutor(
            exchange_config_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="must match configuration.id"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_exchange_config_not_found_error_propagates(self):
        exchange_config_model = exchange_config_executor_test_utils.minimal_exchange_config(
            config_id="missing-config",
        )
        inner = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="missing-config",
            configuration=exchange_config_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-missing",
            configuration=exchange_config_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.update_exchange_config.side_effect = collection_errors.ItemNotFoundError("missing-config")
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            return_value=provider_mock,
        ):
            executor = edit_exchange_config_executor.EditExchangeConfigActionExecutor(
                exchange_config_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.ItemNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="exchange_config",
            expect_error_details=True,
            expected_error_message=protocol_models.ExchangeConfigActionResultErrorMessage.EXCHANGE_CONFIG_NOT_FOUND,
        )
