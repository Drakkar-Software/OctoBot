import asyncio
import datetime
import tempfile

import mock
import pytest

import octobot_node.constants as octobot_node_constants
import octobot_sync.server as sync_server_module
import octobot_node.scheduler
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_protocol.models as protocol_models

import tests.scheduler as scheduler_tests

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_USER_ID = sync_server_module.derive_user_id(_TEST_PRIVATE_KEY)
_MISSING_AUTOMATION_ID = "functional-missing-automation-workflow"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0


@pytest.fixture
def patched_user_action_workflow_max_iteration_retries():
    with mock.patch.object(octobot_node_constants, "USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 2):
        yield


@pytest.fixture
def temp_dbos_scheduler_signal_automation_user_action(
    patched_user_action_workflow_max_iteration_retries,  # noqa: ARG001
):
    with tempfile.NamedTemporaryFile() as temp_file:
        dbos_runtime = scheduler_tests.init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos_runtime.destroy()


def _wrap_configuration(payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(payload.to_json())


def _build_forced_trigger_signal_user_action(
    *,
    user_action_id: str,
    automation_id: str,
) -> protocol_models.UserAction:
    sample_timestamp = datetime.datetime(2026, 5, 1, 12, 0, 0, tzinfo=datetime.UTC)
    payload = protocol_models.SignalAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_SIGNAL,
        automation_id=automation_id,
        signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
    )
    return protocol_models.UserAction(
        id=user_action_id,
        status=protocol_models.UserActionStatus.PENDING,
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        configuration=_wrap_configuration(payload),
    )


async def _run_user_action_to_completion(
    user_id: str,
    user_action: protocol_models.UserAction,
) -> str:
    workflow_id = await scheduler_tasks.trigger_user_action_workflow(user_action, user_id)
    workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)
    await asyncio.wait_for(workflow_handle.get_result(), timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS)
    return workflow_id


@pytest.mark.asyncio
class TestExecuteUserActionSignalAutomationFailureReporting:
    async def test_signal_automation_reports_automation_not_found_when_no_active_workflow(
        self,
        temp_dbos_scheduler_signal_automation_user_action,
    ):
        signal_user_action = _build_forced_trigger_signal_user_action(
            user_action_id="ua-signal-missing-automation",
            automation_id=_MISSING_AUTOMATION_ID,
        )

        await _run_user_action_to_completion(_TEST_USER_ID, signal_user_action)

        listed_user_actions = await scheduler_api.list_user_actions(
            _TEST_USER_ID,
            active_only=True,
        )
        assert len(listed_user_actions) == 1
        listed_user_action = listed_user_actions[0]
        assert listed_user_action.id == signal_user_action.id
        assert listed_user_action.status == protocol_models.UserActionStatus.FAILED
        assert listed_user_action.result is not None
        result_inner = listed_user_action.result.actual_instance
        assert isinstance(result_inner, protocol_models.AutomationActionResult)
        assert result_inner.result_type == protocol_models.UserActionResultType.AUTOMATION
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND
        assert result_inner.error_details is not None
        assert _MISSING_AUTOMATION_ID in result_inner.error_details
