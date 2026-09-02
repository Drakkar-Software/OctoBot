import mock
import pytest

import octobot_flow.enums

import octobot_node.scheduler.automations.signal_execution_result_util as signal_execution_result_util
import octobot_node.scheduler.workflows.params as workflow_params


class TestBuildSignalExecutionResultPayload:
    def test_builds_results_for_all_action_details(self):
        envelope = workflow_params.AutomationWorkflowActionUpdate(
            actions_type="user_actions",
            actions_details=[
                {"id": "action_1", "dsl_script": "noop()"},
                {"id": "action_2", "dsl_script": "noop()"},
            ],
            execution_result_callback=workflow_params.AutomationWorkflowExecutionResultCallback(
                reply_workflow_id="ua-workflow",
                user_action_id="ua-1",
            ),
        )
        processed_action = mock.Mock()
        processed_action.id = "action_1"
        processed_action.error_status = octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
        processed_action.error_message = "missing funds"

        payload = signal_execution_result_util.build_signal_execution_result_payload(
            envelope,
            [processed_action],
        )

        assert payload is not None
        assert payload.user_action_id == "ua-1"
        assert len(payload.priority_action_results) == 2
        assert payload.priority_action_results[0].error_status == "not_enough_funds"
        assert payload.priority_action_results[1].error_status == (
            octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value
        )

    def test_returns_none_without_callback(self):
        envelope = workflow_params.AutomationWorkflowActionUpdate(
            actions_type="user_actions",
            actions_details=[{"id": "action_1", "dsl_script": "noop()"}],
        )
        assert signal_execution_result_util.build_signal_execution_result_payload(envelope, []) is None

    def test_propagates_iteration_error_to_unprocessed_actions(self):
        envelope = workflow_params.AutomationWorkflowActionUpdate(
            actions_type="user_actions",
            actions_details=[
                {"id": "action_1", "dsl_script": "noop()"},
                {"id": "action_2", "dsl_script": "noop()"},
            ],
            execution_result_callback=workflow_params.AutomationWorkflowExecutionResultCallback(
                reply_workflow_id="ua-workflow",
                user_action_id="ua-1",
            ),
        )

        payload = signal_execution_result_util.build_signal_execution_result_payload(
            envelope,
            [],
            iteration_error="pending_priority_actions_skipped",
            iteration_error_message="stale priority skipped",
        )

        assert payload is not None
        assert payload.iteration_error == "pending_priority_actions_skipped"
        assert payload.iteration_error_message == "stale priority skipped"
        assert payload.priority_action_results[0].error_status == "pending_priority_actions_skipped"
        assert payload.priority_action_results[0].error_message == "stale priority skipped"
        assert payload.priority_action_results[1].error_status == "pending_priority_actions_skipped"
        assert payload.priority_action_results[1].error_message == "stale priority skipped"
