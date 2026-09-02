import pytest

pytest.importorskip("octobot_flow")

import octobot_flow.enums
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation as signal_automation_executor
import octobot_node.scheduler.workflows.params as workflow_params


_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"


def _signal_user_action(user_action_id: str = "ua-apply-result") -> protocol_models.UserAction:
    configuration_inner = protocol_models.SignalAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_SIGNAL,
        automation_id="00000000-0000-4000-8000-000000000099",
        signal_type=protocol_models.AutomationSignalType.ACTIONS,
    )
    wrapped_configuration = protocol_models.UserActionConfiguration.from_json(
        configuration_inner.to_json(),
    )
    return protocol_models.UserAction(id=user_action_id, configuration=wrapped_configuration)


def _execution_result(
    *,
    user_action_id: str,
    priority_action_results: list[workflow_params.PriorityActionExecutionResult],
    iteration_error: str | None = None,
    iteration_error_message: str | None = None,
) -> workflow_params.AutomationWorkflowSignalExecutionResult:
    return workflow_params.AutomationWorkflowSignalExecutionResult(
        user_action_id=user_action_id,
        priority_action_results=priority_action_results,
        iteration_error=iteration_error,
        iteration_error_message=iteration_error_message,
    )


class TestApplySignalExecutionResult:
    def test_all_actions_success_marks_completed(self):
        user_action = _signal_user_action()
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        sent_action_ids = ["action_0", "action_1"]
        execution_result = _execution_result(
            user_action_id=user_action.id,
            priority_action_results=[
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_0",
                    error_status=octobot_flow.enums.ActionErrorStatus.NO_ERROR.value,
                ),
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_1",
                    error_status=None,
                ),
            ],
        )

        executor.apply_signal_execution_result(user_action, execution_result, sent_action_ids)

        assert user_action.status == protocol_models.UserActionStatus.COMPLETED
        result_inner = user_action.result.actual_instance
        assert len(result_inner.signal_execution_results) == 2
        assert {result.priority_action_id for result in result_inner.signal_execution_results} == set(
            sent_action_ids,
        )

    def test_trading_error_maps_to_failed_with_results(self):
        user_action = _signal_user_action()
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        sent_action_ids = ["action_0"]
        execution_result = _execution_result(
            user_action_id=user_action.id,
            priority_action_results=[
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_0",
                    error_status=octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
                    error_message="missing funds",
                ),
            ],
        )

        executor.apply_signal_execution_result(user_action, execution_result, sent_action_ids)

        assert user_action.status == protocol_models.UserActionStatus.FAILED
        result_inner = user_action.result.actual_instance
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.NOT_ENOUGH_FUNDS
        assert len(result_inner.signal_execution_results) == 1

    def test_iteration_error_marks_failed(self):
        user_action = _signal_user_action()
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        sent_action_ids = ["action_0"]
        execution_result = _execution_result(
            user_action_id=user_action.id,
            priority_action_results=[
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_0",
                    error_status=None,
                ),
            ],
            iteration_error="iteration_failed",
            iteration_error_message="automation iteration failed",
        )

        executor.apply_signal_execution_result(user_action, execution_result, sent_action_ids)

        assert user_action.status == protocol_models.UserActionStatus.FAILED
        result_inner = user_action.result.actual_instance
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.EXECUTION_FAILED
        assert result_inner.error_details == "automation iteration failed"

    def test_missing_sent_action_id_raises(self):
        user_action = _signal_user_action()
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        execution_result = _execution_result(
            user_action_id=user_action.id,
            priority_action_results=[
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_0",
                    error_status=None,
                ),
            ],
        )

        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="action_1"):
            executor.apply_signal_execution_result(
                user_action,
                execution_result,
                ["action_0", "action_1"],
            )

    def test_unknown_action_error_status_maps_to_execution_failed(self):
        user_action = _signal_user_action()
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        sent_action_ids = ["action_0"]
        execution_result = _execution_result(
            user_action_id=user_action.id,
            priority_action_results=[
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id="action_0",
                    error_status="unexpected_status",
                    error_message="unknown",
                ),
            ],
        )

        executor.apply_signal_execution_result(user_action, execution_result, sent_action_ids)

        assert user_action.status == protocol_models.UserActionStatus.FAILED
        result_inner = user_action.result.actual_instance
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.EXECUTION_FAILED
