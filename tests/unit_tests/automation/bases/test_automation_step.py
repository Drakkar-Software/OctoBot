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
import time

import pytest

from octobot.automation.bases.automation_step import AutomationStep
from octobot.automation.bases.execution_details import ExecutionDetails


class ConcreteAutomationStep(AutomationStep):
    @staticmethod
    def get_description() -> str:
        return "Concrete step for testing"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass


class TestAutomationStep:
    def test_init(self):
        step = ConcreteAutomationStep()
        assert step.last_execution_details is not None
        assert step.last_execution_details.timestamp == 0
        assert step.last_execution_details.description is None
        assert step.last_execution_details.source is None
        assert step.logger is not None

    def test_get_name(self):
        assert ConcreteAutomationStep.get_name() == "ConcreteAutomationStep"

    def test_get_execution_description_default(self):
        step = ConcreteAutomationStep()
        assert step.get_execution_description() is None

    def test_get_user_inputs_raises_not_implemented(self):
        base_step = AutomationStep()
        with pytest.raises(NotImplementedError):
            base_step.get_user_inputs(None, {}, "step")

    def test_apply_config_raises_not_implemented(self):
        base_step = AutomationStep()
        with pytest.raises(NotImplementedError):
            base_step.apply_config({})

    def test_get_description_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            AutomationStep.get_description()

    def test_update_last_execution_details_with_description(self):
        step = ConcreteAutomationStep()
        before = time.time()
        step.update_last_execution_details(description="Test description")
        after = time.time()
        assert step.last_execution_details.description == "Test description"
        assert before <= step.last_execution_details.timestamp <= after + 0.1

    def test_update_last_execution_details_with_source(self):
        step = ConcreteAutomationStep()
        exec_details = ExecutionDetails(100.0, "Source", None)
        step.update_last_execution_details(source=exec_details)
        assert step.last_execution_details.source is not None
        assert step.last_execution_details.source.timestamp == exec_details.timestamp

    def test_update_last_execution_details_uses_deep_copy_for_source(self):
        step = ConcreteAutomationStep()
        exec_details = ExecutionDetails(100.0, "Source", None)
        step.update_last_execution_details(source=exec_details)
        assert step.last_execution_details.source is not exec_details
        assert step.last_execution_details.source.timestamp == exec_details.timestamp
