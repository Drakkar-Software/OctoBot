#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import typing

import octobot_flow.enums

import octobot_node.scheduler.workflows.params as workflow_params


def is_successful_priority_action_error_status(error_status: typing.Optional[str]) -> bool:
    if error_status is None:
        return True
    return error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value


def build_signal_execution_result_payload(
    envelope: workflow_params.AutomationWorkflowActionUpdate,
    processed_actions: list,
    iteration_error: typing.Optional[str] = None,
    iteration_error_message: typing.Optional[str] = None,
) -> typing.Optional[workflow_params.AutomationWorkflowSignalExecutionResult]:
    execution_result_callback = envelope.execution_result_callback
    if execution_result_callback is None:
        return None
    processed_actions_by_id = {
        processed_action.id: processed_action for processed_action in processed_actions
    }
    priority_action_results: list[workflow_params.PriorityActionExecutionResult] = []
    for action_details in envelope.actions_details:
        priority_action_id = action_details["id"]
        processed_action = processed_actions_by_id.get(priority_action_id)
        if processed_action is not None:
            priority_action_results.append(
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id=priority_action_id,
                    error_status=processed_action.error_status,
                    error_message=processed_action.error_message,
                )
            )
        else:
            priority_action_results.append(
                workflow_params.PriorityActionExecutionResult(
                    priority_action_id=priority_action_id,
                    error_status=iteration_error or octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value,
                    error_message=iteration_error_message,
                )
            )
    return workflow_params.AutomationWorkflowSignalExecutionResult(
        user_action_id=execution_result_callback.user_action_id,
        priority_action_results=priority_action_results,
        iteration_error=iteration_error,
        iteration_error_message=iteration_error_message,
    )
