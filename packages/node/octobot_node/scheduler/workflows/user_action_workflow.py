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
import time

import pydantic

import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_node.errors as errors
import octobot_node.enums as node_enums
import octobot_node.scheduler.workflows.params as params
import octobot_node.constants as constants
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_node.scheduler.user_actions.user_actions_executor as user_actions_executor


from octobot_node.scheduler import SCHEDULER  # avoid circular import


async def _recv_signal_execution_result(
    *,
    user_action_id: str,
    sent_action_ids: list[str],
    timeout_seconds: float,
) -> params.AutomationWorkflowSignalExecutionResult:
    import octobot_node.scheduler  # avoid circular import
    if not octobot_node.scheduler.is_initialized():
        raise RuntimeError("Scheduler is not initialized")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        remaining_seconds = deadline - time.monotonic()
        recv_timeout_seconds = min(
            remaining_seconds,
            constants.SIGNAL_EXECUTION_RESULT_RECV_POLL_INTERVAL_SECONDS,
        )
        if recv_timeout_seconds <= 0:
            break
        recv_payload = await SCHEDULER.INSTANCE.recv_async(
            topic=node_enums.AutomationWorkflowMessageTopics.SIGNAL_EXECUTION_RESULT.value,
            timeout_seconds=recv_timeout_seconds,
        )
        if not recv_payload:
            continue
        execution_result = params.AutomationWorkflowSignalExecutionResult.from_dict(recv_payload)
        if execution_result.user_action_id != user_action_id:
            continue
        priority_action_results_by_id = {
            priority_action_result.priority_action_id: priority_action_result
            for priority_action_result in execution_result.priority_action_results
        }
        if not all(action_id in priority_action_results_by_id for action_id in sent_action_ids):
            continue
        return execution_result
    raise errors.SignalExecutionResultTimeoutError(
        f"Timed out after {timeout_seconds:.1f}s waiting for signal execution result "
        f"for user action {user_action_id!r}."
    )


@SCHEDULER.INSTANCE.dbos_class()
class UserActionWorkflow:
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_user_action")
    async def execute_user_action(inputs: dict) -> dict:
        dispatch_output = await UserActionWorkflow._dispatch_user_action(inputs)
        parsed_dispatch_output = params.UserActionExecutionResult.from_dict(dispatch_output)
        if parsed_dispatch_output.signal_execution_await_context is not None:
            signal_execution_await_context = parsed_dispatch_output.signal_execution_await_context
            try:
                execution_result = await _recv_signal_execution_result(
                    user_action_id=signal_execution_await_context.user_action_id,
                    sent_action_ids=signal_execution_await_context.sent_action_ids,
                    timeout_seconds=constants.SIGNAL_EXECUTION_RESULT_TIMEOUT_SECONDS,
                )
                execution_result_dict = execution_result.to_dict(include_default_values=False)
            except errors.SignalExecutionResultTimeoutError as timeout_error:
                dispatch_output = await UserActionWorkflow._apply_signal_execution_timeout(
                    inputs,
                    dispatch_output,
                    str(timeout_error),
                )
            else:
                dispatch_output = await UserActionWorkflow._apply_signal_execution_result(
                    inputs,
                    dispatch_output,
                    execution_result_dict,
                )
            parsed_dispatch_output = params.UserActionExecutionResult.from_dict(dispatch_output)
        try:
            await UserActionWorkflow.after_user_action_execution(parsed_dispatch_output)
        except Exception as err:
            parsed_dispatch_output.updated_user_action.status = protocol_models.UserActionStatus.FAILED
            if parsed_dispatch_output.updated_user_action.result and parsed_dispatch_output.updated_user_action.result.actual_instance:
                parsed_dispatch_output.updated_user_action.result.actual_instance.error_details = str(err)[:constants.FAILURE_ERROR_DETAILS_MAX_LENGTH]
        parsed_inputs = params.UserActionWorkflowInputs.from_dict(inputs)
        return params.UserActionWorkflowOutput(
            user_id=parsed_inputs.user_id,
            updated_user_action=parsed_dispatch_output.updated_user_action,
        ).to_dict(include_default_values=False)

    @staticmethod
    def _should_retry(error: BaseException) -> bool:
        return not isinstance(error, (
            # workflow-step failures that should not be retried by DBOS
            errors.WorkflowError,
            errors.UserActionError,
            pydantic.ValidationError,
            trading_errors.AuthenticationError,  # includes credential / IP-whitelist subclasses
            collection_errors.DuplicateItemError,
        ))

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="dispatch_user_action",
        retries_allowed=True,
        interval_seconds=constants.USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS,
        max_attempts=constants.USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES,
        backoff_rate=constants.USER_ACTION_WORKFLOW_BACKOFF_RATE,
        should_retry=_should_retry,
    )
    async def _dispatch_user_action(inputs: dict) -> dict:
        parsed_inputs: params.UserActionWorkflowInputs = params.UserActionWorkflowInputs.from_dict(inputs)
        # Rebuild via JSON, not UserAction.from_dict(inner.to_dict()): nested protocol types
        # (e.g. Account.created_at / updated_at) stay as datetime in to_dict() output, while
        # UserActionConfiguration.from_dict uses json.dumps internally and rejects datetimes.
        if parsed_inputs.user_action and (
            parsed_user_action := protocol_models.UserAction.from_json(
                parsed_inputs.user_action.to_json()
            )
        ):
            executor_class = user_actions_executor.user_action_executor_factory(parsed_user_action)
            executor = executor_class(parsed_inputs.user_id)
            try:
                await executor.execute(parsed_user_action)
            except (errors.UserActionError, collection_errors.DuplicateItemError):
                if parsed_user_action.status != protocol_models.UserActionStatus.FAILED:
                    raise
            return params.UserActionExecutionResult(
                updated_user_action=parsed_user_action,
                post_actions=executor.post_actions,
                signal_execution_await_context=getattr(executor, "signal_execution_await_context", None),
            ).to_dict(include_default_values=False)
        raise errors.WorkflowInputError("No user action found in inputs")

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="apply_signal_execution_result",
        retries_allowed=True,
        interval_seconds=constants.USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS,
        max_attempts=constants.USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES,
        backoff_rate=constants.USER_ACTION_WORKFLOW_BACKOFF_RATE,
        should_retry=_should_retry,
    )
    async def _apply_signal_execution_result(
        inputs: dict,
        dispatch_output: dict,
        execution_result: dict,
    ) -> dict:
        parsed_inputs: params.UserActionWorkflowInputs = params.UserActionWorkflowInputs.from_dict(inputs)
        parsed_dispatch_output = params.UserActionExecutionResult.from_dict(dispatch_output)
        signal_execution_await_context = parsed_dispatch_output.signal_execution_await_context
        if signal_execution_await_context is None:
            return dispatch_output
        parsed_user_action = protocol_models.UserAction.from_json(
            parsed_dispatch_output.updated_user_action.to_json()
        )
        executor_class = user_actions_executor.user_action_executor_factory(parsed_user_action)
        executor = executor_class(parsed_inputs.user_id)
        if not isinstance(executor, user_actions_executor.AutomationUserActionExecutor):
            raise errors.WorkflowInputError(
                f"Expected AutomationUserActionExecutor for signal execution result, got {executor.__class__.__name__}"
            )
        parsed_execution_result = params.AutomationWorkflowSignalExecutionResult.from_dict(execution_result)
        executor.apply_signal_execution_result(
            parsed_user_action,
            parsed_execution_result,
            signal_execution_await_context.sent_action_ids,
        )
        return params.UserActionExecutionResult(
            updated_user_action=parsed_user_action,
            post_actions=parsed_dispatch_output.post_actions,
            signal_execution_await_context=None,
        ).to_dict(include_default_values=False)

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="apply_signal_execution_timeout",
        retries_allowed=True,
        interval_seconds=constants.USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS,
        max_attempts=constants.USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES,
        backoff_rate=constants.USER_ACTION_WORKFLOW_BACKOFF_RATE,
        should_retry=_should_retry,
    )
    async def _apply_signal_execution_timeout(
        inputs: dict,
        dispatch_output: dict,
        timeout_error_message: str,
    ) -> dict:
        parsed_inputs: params.UserActionWorkflowInputs = params.UserActionWorkflowInputs.from_dict(inputs)
        parsed_dispatch_output = params.UserActionExecutionResult.from_dict(dispatch_output)
        parsed_user_action = protocol_models.UserAction.from_json(
            parsed_dispatch_output.updated_user_action.to_json()
        )
        executor_class = user_actions_executor.user_action_executor_factory(parsed_user_action)
        executor = executor_class(parsed_inputs.user_id)
        if not isinstance(executor, user_actions_executor.AutomationUserActionExecutor):
            raise errors.WorkflowInputError(
                f"Expected AutomationUserActionExecutor for signal execution timeout, got {executor.__class__.__name__}"
            )
        executor.apply_signal_execution_timeout(
            parsed_user_action,
            errors.SignalExecutionResultTimeoutError(timeout_error_message),
        )
        return params.UserActionExecutionResult(
            updated_user_action=parsed_user_action,
            post_actions=parsed_dispatch_output.post_actions,
            signal_execution_await_context=None,
        ).to_dict(include_default_values=False)

    @staticmethod
    async def after_user_action_execution(output: params.UserActionExecutionResult) -> None:
        if output.post_actions.to_create_automation_task:
            await scheduler_tasks.trigger_task(
                output.post_actions.to_create_automation_task,
                target_workflow_id=output.post_actions.to_create_automation_task.id
            )
        if output.post_actions.portfolio_history_collection_params:
            await scheduler_tasks.trigger_portfolio_history_collection(
                output.post_actions.portfolio_history_collection_params,
            )
