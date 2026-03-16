import pytest
import mock
import time

import octobot_flow
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    resolved_actions,
    automation_state_dict,
)


@pytest.fixture
def init_action():
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {"automation_id": "automation_1"},
            },
        },
    }


@pytest.fixture
def stop_automation_action():
    return {
        "id": "action_stop",
        "dsl_script": "stop_automation()",
        "dependencies": [
            {"action_id": "action_init"},
        ],
    }


@pytest.fixture
def random_action():
    return {
        "id": "action_random",
        "dsl_script": "'yes' if 1 == 2 else 'no'",
        "dependencies": [
            {"action_id": "action_init"},
        ],
    }

@pytest.mark.asyncio
async def test_stop_automation_action_sets_post_actions_stop_flag(
    init_action: dict,
    stop_automation_action: dict,
):
    all_actions = [init_action, stop_automation_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        # 1. Initialize with configuration (only init action is executed)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as init_automation_job:
            await init_automation_job.run()
        assert init_automation_job.automation_state.automation.post_actions.stop_automation is False

        # 2. Run again to execute the stop_automation action
        after_config_execution_dump = init_automation_job.dump()
        state = after_config_execution_dump
        async with octobot_flow.AutomationJob(state, [], {}) as automation_job:
            await automation_job.run()

        # 3. Verify stop_automation action was executed and post_actions.stop_automation is set
        actions = automation_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(all_actions)
        for action in actions:
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time

        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        assert automation_job.automation_state.priority_actions == []


@pytest.mark.asyncio
async def test_stop_automation_action_via_priority_actions_sets_post_actions_stop_flag(
    init_action: dict,
    stop_automation_action: dict,
    random_action: dict,
):
    all_actions = [init_action, random_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        # 1. Initialize with configuration (only init action is executed)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as init_automation_job:
            await init_automation_job.run()
        assert init_automation_job.automation_state.automation.post_actions.stop_automation is False
        # check random action is not executed
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].result is None
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None

        # 2. Run again with stop_automation_action as priority_actions
        after_config_execution_dump = init_automation_job.dump()
        state = after_config_execution_dump
        priority_actions = resolved_actions([stop_automation_action])
        async with octobot_flow.AutomationJob(state, priority_actions, {}) as automation_job:
            await automation_job.run()
        # check random action is not executed
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].result is None
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None

        # check stop_automation action is executed
        assert priority_actions[0].executed_at is not None and priority_actions[0].executed_at >= current_time

        # 3. Verify stop_automation action was executed and post_actions.stop_automation is set
        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        assert automation_job.automation_state.priority_actions == priority_actions
        # ensure priority_actions is added to history
