#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
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

import octobot_node.scheduler.user_actions.user_actions_executor.account_user_action_executor as account_user_action_executor


class _AccountChannelTestExecutor(account_user_action_executor.AccountUserActionExecutor):
    async def _do_execute(self, user_action: protocol_models.UserAction) -> None:
        self._mark_user_action_completed(user_action)


class TestUserActionExecutorExecuteHooks:
    @pytest.mark.asyncio
    async def test_execute_sets_running_then_completed_on_model(self):
        user_action = protocol_models.UserAction(id="ua-hook-1", configuration=None)
        executor = _AccountChannelTestExecutor("0xwallet")
        await executor.execute(user_action)
        assert user_action.status == protocol_models.UserActionStatus.COMPLETED
        assert user_action.result is not None
        assert isinstance(user_action.result.actual_instance, protocol_models.AccountActionResult)

    @pytest.mark.asyncio
    async def test_execute_mocks_do_execute_and_sets_completed_on_model(self):
        user_action = protocol_models.UserAction(id="ua-hook-2", configuration=None)
        executor = _AccountChannelTestExecutor("0xwallet")

        async def fake_do(user_action_model: protocol_models.UserAction) -> None:
            executor._mark_user_action_completed(user_action_model)

        mock_do = mock.AsyncMock(side_effect=fake_do)
        with mock.patch.object(executor, "_do_execute", mock_do):
            await executor.execute(user_action)
        mock_do.assert_awaited_once_with(user_action)
        assert user_action.status == protocol_models.UserActionStatus.COMPLETED
