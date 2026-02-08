#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest

from octobot.automation.bases.abstract_action import AbstractAction
from octobot.automation.bases.execution_details import ExecutionDetails


class ConcreteAction(AbstractAction):
    @staticmethod
    def get_description() -> str:
        return "Concrete action"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def process(self, execution_details: ExecutionDetails) -> bool:
        return True


class FailingAction(AbstractAction):
    @staticmethod
    def get_description() -> str:
        return "Failing action"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def process(self, execution_details: ExecutionDetails) -> bool:
        return False


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestAbstractAction:
    async def test_call_process_returns_true_when_process_succeeds(self):
        action = ConcreteAction()
        exec_details = ExecutionDetails(100.0, "Test", None)
        result = await action.call_process(exec_details)
        assert result is True

    async def test_call_process_returns_false_when_process_fails(self):
        action = FailingAction()
        exec_details = ExecutionDetails(100.0, "Test", None)
        result = await action.call_process(exec_details)
        assert result is False

    async def test_call_process_updates_last_execution_details_on_success(self):
        action = ConcreteAction()
        exec_details = ExecutionDetails(100.0, "Test", None)
        await action.call_process(exec_details)
        assert action.last_execution_details.timestamp > 0

    async def test_call_process_does_not_update_last_execution_details_on_failure(self):
        action = FailingAction()
        initial_timestamp = action.last_execution_details.timestamp
        exec_details = ExecutionDetails(100.0, "Test", None)
        await action.call_process(exec_details)
        assert action.last_execution_details.timestamp == initial_timestamp
