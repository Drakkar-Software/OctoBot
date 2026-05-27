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

import datetime

import mock
import pytest

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.account_auth.create_account_auth as create_account_auth_executor

from . import account_auth_executor_test_utils
from .. import provider_assertions

_FIXED_TIMESTAMP = datetime.datetime(2026, 5, 31, 10, 0, 0, tzinfo=datetime.UTC)
_OLD_CLIENT_TIMESTAMP = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)


class TestCreateAccountAuthActionExecutorExecute:
    @pytest.mark.asyncio
    async def test_calls_provider_create_with_wallet_and_authentication(self):
        authentication_model = account_auth_executor_test_utils.minimal_account_authentication(
            auth_id="new-auth",
        )
        inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=authentication_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-create-auth",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with (
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountAuthenticationProvider.instance",
                return_value=provider_mock,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.account_auth.account_auth_user_action_executor.timestamp_util.utc_now_datetime",
                return_value=_FIXED_TIMESTAMP,
            ),
        ):
            executor = create_account_auth_executor.CreateAccountAuthActionExecutor(
                account_auth_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        provider_mock.create_item.assert_called_once_with(
            account_auth_executor_test_utils.WALLET_ADDRESS,
            authentication_model.model_copy(update={"updated_at": _FIXED_TIMESTAMP}),
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="account_auth",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_overwrites_client_updated_at_before_create(self):
        authentication_model = account_auth_executor_test_utils.minimal_account_authentication(
            auth_id="new-auth",
            updated_at=_OLD_CLIENT_TIMESTAMP,
        )
        inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=authentication_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-create-auth-stamp",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        with (
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountAuthenticationProvider.instance",
                return_value=provider_mock,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.account_auth.account_auth_user_action_executor.timestamp_util.utc_now_datetime",
                return_value=_FIXED_TIMESTAMP,
            ),
        ):
            executor = create_account_auth_executor.CreateAccountAuthActionExecutor(
                account_auth_executor_test_utils.WALLET_ADDRESS,
            )
            await executor.execute(user_action)
        passed_authentication = provider_mock.create_item.call_args[0][1]
        assert passed_authentication.updated_at == _FIXED_TIMESTAMP

    @pytest.mark.asyncio
    async def test_raises_when_configuration_missing(self):
        user_action = protocol_models.UserAction(id="ua-bad", configuration=None)
        executor = create_account_auth_executor.CreateAccountAuthActionExecutor(
            account_auth_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="create-account-auth configuration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account_auth",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountAuthActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_payload_type_wrong(self):
        inner = protocol_models.DeleteAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_DELETE,
            id="auth-1",
        )
        user_action = protocol_models.UserAction(
            id="ua-wrong",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        executor = create_account_auth_executor.CreateAccountAuthActionExecutor(
            account_auth_executor_test_utils.WALLET_ADDRESS,
        )
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="CreateAccountAuthConfiguration"):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account_auth",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountAuthActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_duplicate_account_auth_error_propagates(self):
        authentication_model = account_auth_executor_test_utils.minimal_account_authentication(
            auth_id="dup-auth",
        )
        inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=authentication_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-dup",
            configuration=account_auth_executor_test_utils.wrap_configuration(inner),
        )
        provider_mock = mock.Mock()
        provider_mock.create_item.side_effect = collection_errors.DuplicateItemError("dup-auth")
        with mock.patch(
            "octobot_sync.sync.collection_providers.AccountAuthenticationProvider.instance",
            return_value=provider_mock,
        ):
            executor = create_account_auth_executor.CreateAccountAuthActionExecutor(
                account_auth_executor_test_utils.WALLET_ADDRESS,
            )
            with pytest.raises(collection_errors.DuplicateItemError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="account_auth",
            expect_error_details=True,
            expected_error_message=protocol_models.AccountAuthActionResultErrorMessage.DUPLICATE_ITEM,
        )
