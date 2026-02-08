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

from octobot.automation.bases.abstract_condition import AbstractCondition


class PassingCondition(AbstractCondition):
    @staticmethod
    def get_description() -> str:
        return "Passing condition"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def evaluate(self) -> bool:
        return True


class FailingCondition(AbstractCondition):
    @staticmethod
    def get_description() -> str:
        return "Failing condition"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def evaluate(self) -> bool:
        return False


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestAbstractCondition:
    async def test_call_evaluate_returns_true_when_evaluate_passes(self):
        condition = PassingCondition()
        result = await condition.call_evaluate()
        assert result is True

    async def test_call_evaluate_returns_false_when_evaluate_fails(self):
        condition = FailingCondition()
        result = await condition.call_evaluate()
        assert result is False

    async def test_call_evaluate_updates_last_execution_details_on_success(self):
        condition = PassingCondition()
        await condition.call_evaluate()
        assert condition.last_execution_details.timestamp > 0

    async def test_call_evaluate_does_not_update_last_execution_details_on_failure(self):
        condition = FailingCondition()
        initial_timestamp = condition.last_execution_details.timestamp
        await condition.call_evaluate()
        assert condition.last_execution_details.timestamp == initial_timestamp
