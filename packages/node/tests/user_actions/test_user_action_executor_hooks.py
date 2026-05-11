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

import typing

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.user_actions.user_actions_executor.account_user_action_executor as account_user_action_executor
import octobot_node.user_actions.user_actions_provider as user_actions_provider_module


class _AccountChannelTestExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(self, user_action: protocol_models.UserAction) -> None:
        self._mark_user_action_completed(user_action)


class TestUserActionExecutorExecuteHooks:
    @pytest.mark.asyncio
    async def test_execute_registers_running_then_completed_in_provider(self):
        provider = user_actions_provider_module.UserActionsProvider.instance()
        create_calls_statuses: list[typing.Optional[protocol_models.UserActionStatus]] = []
        original_create = provider.create_user_action

        def create_tracking(wallet_address: str, user_action: protocol_models.UserAction) -> protocol_models.UserAction:
            create_calls_statuses.append(user_action.status)
            return original_create(wallet_address, user_action)

        user_action = protocol_models.UserAction(id="ua-hook-1", configuration=None)
        executor = _AccountChannelTestExecutor("0xwallet")
        with mock.patch.object(provider, "create_user_action", side_effect=create_tracking):
            await executor.execute(user_action)
        assert create_calls_statuses == [protocol_models.UserActionStatus.RUNNING]
        stored = user_actions_provider_module.UserActionsProvider.instance().get_user_action("0xwallet", "ua-hook-1")
        assert stored.status == protocol_models.UserActionStatus.COMPLETED
        assert stored.result is not None
        assert isinstance(stored.result.actual_instance, protocol_models.AccountActionResult)

    @pytest.mark.asyncio
    async def test_execute_mocks_do_execute_and_still_flushes_provider(self):
        user_action = protocol_models.UserAction(id="ua-hook-2", configuration=None)
        executor = _AccountChannelTestExecutor("0xwallet")

        async def fake_do(user_action_model: protocol_models.UserAction) -> None:
            executor._mark_user_action_completed(user_action_model)

        mock_do = mock.AsyncMock(side_effect=fake_do)
        with mock.patch.object(executor, "_do_execute", mock_do):
            await executor.execute(user_action)
        mock_do.assert_awaited_once_with(user_action)
        stored = user_actions_provider_module.UserActionsProvider.instance().get_user_action("0xwallet", "ua-hook-2")
        assert stored.status == protocol_models.UserActionStatus.COMPLETED
