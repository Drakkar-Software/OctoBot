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
from mock import Mock, patch, AsyncMock

from octobot.automation.automation import Automation, AutomationDetails
from octobot.automation.bases.abstract_trigger_event import AbstractTriggerEvent
from octobot.automation.bases.abstract_condition import AbstractCondition
from octobot.automation.bases.abstract_action import AbstractAction
from octobot.automation.bases.execution_details import ExecutionDetails
from octobot.automation.bases import automation_step
import octobot.errors as errors


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestLastExecutionDetailsUpdater:
    """Tests for automation_step.last_execution_details_updater decorator."""

    async def test_updates_last_execution_details_when_result_is_truthy(self):
        class StepWithDecorator:
            def __init__(self):
                self.last_execution_details = ExecutionDetails(0, None, None)

            def update_last_execution_details(self, description=None, source=None):
                self.update_called = True

            @automation_step.last_execution_details_updater
            async def do_something(self):
                return True

        step = StepWithDecorator()
        step.update_called = False
        result = await step.do_something()
        assert result is True
        assert step.update_called is True

    async def test_does_not_update_when_result_is_falsy(self):
        class StepWithDecorator:
            def __init__(self):
                self.last_execution_details = ExecutionDetails(0, None, None)

            def update_last_execution_details(self, description=None, source=None):
                self.update_called = True

            @automation_step.last_execution_details_updater
            async def do_something(self):
                return False

        step = StepWithDecorator()
        step.update_called = False
        result = await step.do_something()
        assert result is False
        assert step.update_called is False

    async def test_preserves_return_value(self):
        class StepWithDecorator:
            def __init__(self):
                self.last_execution_details = ExecutionDetails(0, None, None)

            def update_last_execution_details(self, description=None, source=None):
                pass

            @automation_step.last_execution_details_updater
            async def do_something(self):
                return {"key": "value"}

        step = StepWithDecorator()
        result = await step.do_something()
        assert result == {"key": "value"}


class MockTriggerEvent(AbstractTriggerEvent):
    @staticmethod
    def get_description() -> str:
        return "MockTrigger"

    def get_user_inputs(self, UI, inputs, step_name): return {}

    def apply_config(self, config): pass

    async def _get_next_event(self):
        pass


class MockCondition(AbstractCondition):
    @staticmethod
    def get_description() -> str:
        return "MockCondition"

    def get_user_inputs(self, UI, inputs, step_name): return {}

    def apply_config(self, config): pass

    async def process(self, execution_details: ExecutionDetails) -> bool:
        return True


class MockAction(AbstractAction):
    @staticmethod
    def get_description() -> str:
        return "MockAction"

    def get_user_inputs(self, UI, inputs, step_name): return {}

    def apply_config(self, config): pass

    async def process(self, execution_details: ExecutionDetails) -> bool:
        return True


class TestAutomationDetails:
    def test_init(self):
        trigger = MockTriggerEvent()
        conditions = [MockCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        assert details.trigger_event is trigger
        assert details.conditions == conditions
        assert details.actions == actions

    def test_str(self):
        trigger = MockTriggerEvent()
        conditions = [MockCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        result = str(details)
        assert "MockTrigger" in result
        assert "MockCondition" in result
        assert "MockAction" in result


class TestAutomation:
    @pytest.fixture
    def mock_tentacles_setup_config(self):
        return Mock()

    @pytest.fixture
    def automation(self, mock_tentacles_setup_config):
        with patch("octobot.automation.automation.constants") as mock_constants:
            mock_constants.ENABLE_AUTOMATIONS = True
            return Automation(
                bot_id="test-bot",
                tentacles_setup_config=mock_tentacles_setup_config,
                automations_config={}
            )

    def test_init(self, automation, mock_tentacles_setup_config):
        assert automation.bot_id == "test-bot"
        assert automation.tentacles_setup_config is mock_tentacles_setup_config
        assert automation.automations_config == {}
        assert automation.automation_tasks == []
        assert automation.automation_details == []
        assert automation.logger is not None

    def test_get_local_config(self, automation):
        automation.automations_config = {"key": "value"}
        assert automation.get_local_config() == {"key": "value"}

    def test_automation_constants(self):
        assert Automation.AUTOMATION == "automation"
        assert Automation.AUTOMATIONS == "automations"
        assert Automation.AUTOMATIONS_COUNT == "automations_count"
        assert Automation.TRIGGER_EVENT == "trigger_event"
        assert Automation.CONDITIONS == "conditions"
        assert Automation.ACTIONS == "actions"

    async def test_initialize_when_automations_disabled(self, mock_tentacles_setup_config):
        with patch("octobot.automation.automation.constants") as mock_constants:
            mock_constants.ENABLE_AUTOMATIONS = False
            automation = Automation("bot", mock_tentacles_setup_config, {})
            await automation.initialize()
        # Should not raise, just logs

    async def test_initialize_when_automations_enabled(self, mock_tentacles_setup_config):
        with patch("octobot.automation.automation.constants") as mock_constants:
            mock_constants.ENABLE_AUTOMATIONS = True
            automation = Automation("bot", mock_tentacles_setup_config, {})
            with patch.object(automation, "restart", new_callable=AsyncMock):
                await automation.initialize()
                automation.restart.assert_awaited_once()

    async def test_restart_raises_when_disabled(self, mock_tentacles_setup_config):
        import octobot.errors as errors
        with patch("octobot.automation.automation.constants") as mock_constants:
            mock_constants.ENABLE_AUTOMATIONS = False
            automation = Automation("bot", mock_tentacles_setup_config, {})
            with pytest.raises(errors.DisabledError, match="disabled"):
                await automation.restart()

    def test_is_valid_automation_config(self, automation):
        assert automation._is_valid_automation_config(
            {automation.TRIGGER_EVENT: "SomeTrigger"}
        ) is True
        assert automation._is_valid_automation_config(
            {automation.TRIGGER_EVENT: None}
        ) is False
        assert automation._is_valid_automation_config({}) is False

    def test_create_local_instance(self, mock_tentacles_setup_config):
        config = {}
        tentacle_config = {"automations_count": 0}
        instance = Automation.create_local_instance(
            config, mock_tentacles_setup_config, tentacle_config
        )
        assert isinstance(instance, Automation)
        assert instance.bot_id is None
        assert instance.automations_config == tentacle_config

    def test_get_all_steps(self, automation):
        with patch("octobot.automation.automation.tentacles_management.get_all_classes_from_parent") as mock_get_classes:
            mock_get_classes.side_effect = [
                [MockTriggerEvent],
                [MockCondition],
                [MockAction],
            ]
            events, conditions, actions = automation.get_all_steps()
            assert "MockTriggerEvent" in events
            assert "MockCondition" in conditions
            assert "MockAction" in actions

    async def test_check_conditions_all_pass(self, automation):
        trigger = MockTriggerEvent()
        conditions = [MockCondition(), MockCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        exec_details = ExecutionDetails(100.0, "Test", None)
        result = await automation._check_conditions(details, exec_details)
        assert result is True

    async def test_check_conditions_one_fails(self, automation):
        class FailingCondition(AbstractCondition):
            @staticmethod
            def get_description() -> str:
                return "Failing"

            def get_user_inputs(self, UI, inputs, step_name): return {}

            def apply_config(self, config): pass

            async def process(self, execution_details: ExecutionDetails) -> bool:
                return False

        trigger = MockTriggerEvent()
        conditions = [MockCondition(), FailingCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        exec_details = ExecutionDetails(100.0, "Test", None)
        result = await automation._check_conditions(details, exec_details)
        assert result is False

    async def test_process_actions(self, automation):
        trigger = MockTriggerEvent()
        conditions = [MockCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        exec_details = ExecutionDetails(100.0, "Test", None)
        await automation._process_actions(details, exec_details)
        # Should not raise

    async def test_run_automation(self, automation):
        trigger = MockTriggerEvent()
        conditions = [MockCondition()]
        actions = [MockAction()]
        details = AutomationDetails(trigger, conditions, actions)
        exec_details = ExecutionDetails(100.0, "Test", None)

        async def _ok_next_execution():
            yield exec_details
            yield exec_details

        with patch.object(trigger, "next_execution", _ok_next_execution), \
            patch.object(actions[0], "process", AsyncMock(return_value=True)) as mock_process:
            await automation._run_automation(details)
            # Should not raise, called twice: once for each yield
            assert mock_process.call_count == 2

        async def _raising_next_execution():
            yield exec_details
            raise errors.AutomationStopped

        with patch.object(trigger, "next_execution", _raising_next_execution), \
            patch.object(actions[0], "process", AsyncMock(return_value=True)) as mock_process:
            await automation._run_automation(details)
            # Should not raise, called only once
            assert mock_process.call_count == 1
