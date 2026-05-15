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
import pydantic

import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors
import octobot_node.errors as errors
import octobot_node.scheduler.workflows.params as params
import octobot_node.constants as constants
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_node.scheduler.user_actions.user_actions_executor as user_actions_executor


from octobot_node.scheduler import SCHEDULER  # avoid circular import


@SCHEDULER.INSTANCE.dbos_class()
class UserActionWorkflow:
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_user_action")
    async def execute_user_action(inputs: dict) -> dict:
        output = await UserActionWorkflow._execute_user_action(inputs)
        parsed_output = params.UserActionExecutionResult.from_dict(output)
        try:
            await UserActionWorkflow.after_user_action_execution(parsed_output)
        except Exception as err:
            parsed_output.updated_user_action.status = protocol_models.UserActionStatus.FAILED
            if parsed_output.updated_user_action.result and parsed_output.updated_user_action.result.actual_instance:
                parsed_output.updated_user_action.result.actual_instance.error_details = str(err)[:constants.FAILURE_ERROR_DETAILS_MAX_LENGTH]
        parsed_inputs = params.UserActionWorkflowInputs.from_dict(inputs)
        return params.UserActionWorkflowOutput(
            wallet_address=parsed_inputs.wallet_address,
            updated_user_action=parsed_output.updated_user_action,
        ).to_dict(include_default_values=False)

    @staticmethod
    def _should_retry(error: BaseException) -> bool:
        return not isinstance(error, (
            # workflow-step failures that should not be retried by DBOS
            errors.WorkflowActionExecutionError,
            errors.UserActionError,
            pydantic.ValidationError,
            trading_errors.AuthenticationError,  # includes credential / IP-whitelist subclasses
        ))

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="execute_user_action",
        retries_allowed=True,
        interval_seconds=constants.USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS,
        max_attempts=constants.USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES,
        backoff_rate=constants.USER_ACTION_WORKFLOW_BACKOFF_RATE,
        should_retry=_should_retry,
    )
    async def _execute_user_action(inputs: dict) -> dict:
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
            executor = executor_class(parsed_inputs.wallet_address)
            await executor.execute(parsed_user_action)
            return params.UserActionExecutionResult(
                updated_user_action=parsed_user_action,
                post_actions=executor.post_actions,
            ).to_dict(include_default_values=False)
        raise errors.WorkflowInputError("No user action found in inputs")

    @staticmethod
    async def after_user_action_execution(output: params.UserActionExecutionResult) -> None:
        if output.post_actions.to_create_automation_task:
            await scheduler_tasks.trigger_task(
                output.post_actions.to_create_automation_task,
                target_workflow_id=output.post_actions.to_create_automation_task.id
            )
