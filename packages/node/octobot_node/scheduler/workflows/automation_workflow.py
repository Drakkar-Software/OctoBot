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
import json
import time
import typing

import octobot_commons.logging

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.task_context
import octobot_node.scheduler.workflows.params as params
import octobot_node.errors as errors

if typing.TYPE_CHECKING:
    import octobot_flow.entities

from octobot_node.scheduler import SCHEDULER  # avoid circular import


MAX_ITERATION_RETRIES = 3


@SCHEDULER.INSTANCE.dbos_class()
class AutomationWorkflow:
    # Always use dict as input to parse minimizable dataclasses and facilitate data format updates

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_automation")
    async def execute_automation(inputs: dict) -> None:
        """
        Automation workflow runner: 
        1. Wait for priority actions if any.
        2. Execute the iteration (received priority action or DAG's executable actions).
        3. Check and process other received priority actions if any.
        4. Either:
            A. Reschedule the next iteration as a child workflow to avoid growing the workflow forever.
            B. Complete the workflow and stop the automation.
        """
        try:
            parsed_inputs = params.AutomationWorkflowInputs.from_dict(inputs)
            delay = parsed_inputs.execution_time - time.time()
            delay_str = f" in {delay:.2f} seconds" if delay > 0 else ""
            AutomationWorkflow.get_logger(parsed_inputs).info(f"{AutomationWorkflow.__name__} starting{delay_str}.")
            priority_actions: list[dict] = []
            if delay > 0:
                priority_actions = await AutomationWorkflow._wait_and_trigger_on_priority_actions(
                    parsed_inputs, parsed_inputs.execution_time
                )
            raw_iteration_result = await AutomationWorkflow.execute_iteration(inputs, priority_actions)
            iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
            continue_workflow = False
            if AutomationWorkflow._should_continue_workflow(parsed_inputs, iteration_result.progress_status, bool(priority_actions)):
                continue_workflow = await AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                    parsed_inputs, iteration_result
                )
            if not continue_workflow:
                AutomationWorkflow.get_logger(parsed_inputs).info(
                    f"Stopped workflow (remaining steps: {iteration_result.progress_status.remaining_steps})"
                )
        except Exception as err:
            AutomationWorkflow.get_logger(parsed_inputs).exception(
                err, True, f"Interrupted workflow: unexpected critical error: {err} ({err.__class__.__name__})"
            )

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="execute_iteration", retries_allowed=True, max_attempts=MAX_ITERATION_RETRIES
    )
    async def execute_iteration(inputs: dict, user_actions: list[dict]) -> dict:
        """
        Execute an automation iteration: executed actions can be received priority actions or DAG's executable actions.
        In case of priority actions, the returned next scheduled time will be the same as the previous one to respect
        the latest DAG execution time schedule.

        Should be a SCHEDULER.INSTANCE.step to avoid executing actions twice when recovering a workflow 
        that was interrupted while executing priority actions which were received AFTER the initial 
        iteration of the workflow.

        Will retry up to 3 times in case of an unexpected error before failing step.
        """
        parsed_inputs: params.AutomationWorkflowInputs = params.AutomationWorkflowInputs.from_dict(inputs)
        executed_step: str = "no action executed"
        execution_error = next_iteration_description = next_iteration_description_metadata = next_step = next_step_at = None
        with octobot_node.scheduler.task_context.encrypted_task(parsed_inputs.task):
            #### Start of decryped task context ####
            result: octobot_flow_client.OctoBotActionsJobResult = None # type: ignore
            if parsed_inputs.task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
                if user_actions:
                    AutomationWorkflow.get_logger(parsed_inputs).info(f"Executing user actions: {user_actions}")
                else:
                    AutomationWorkflow.get_logger(parsed_inputs).info(
                        f"Executing {parsed_inputs.task.name} DAG's executable actions"
                    )
                result = await octobot_flow_client.OctoBotActionsJob(
                    parsed_inputs.task.content, user_actions
                ).run()
                if result.processed_actions:
                    if latest_step := AutomationWorkflow._get_actions_summary(result.processed_actions, minimal=True):
                        executed_step = latest_step
                    for action in result.processed_actions:
                        if action.error_status is not None:
                            AutomationWorkflow.get_logger(parsed_inputs).error(
                                f"Error: {action.error_status} when executing action {action.id}: {action.get_summary()} "
                            )
                            execution_error = action.error_status
            if result is None:
                raise errors.WorkflowInputError(f"Invalid task type: {parsed_inputs.task.type}")
            next_actions = []
            remaining_steps = 0
            if result.next_actions_description:
                if result.actions_dag:
                    next_actions = result.actions_dag.get_executable_actions()
                    remaining_steps = len(result.actions_dag.get_pending_actions())
                next_step_at = result.next_actions_description.get_next_execution_time()
                raw_description = json.dumps(
                    result.next_actions_description.to_dict(include_default_values=False)
                )
                next_iteration_description_metadata = None
                if octobot_node.config.settings.is_node_side_encryption_enabled:
                    next_iteration_description, next_iteration_description_metadata = (
                        encryption.encrypt_task_content(raw_description)
                    )
                else:
                    next_iteration_description = raw_description
                next_step = AutomationWorkflow._get_actions_summary(next_actions, minimal=True)
            AutomationWorkflow.get_logger(parsed_inputs).info(
                f"Iteration completed, executed step: '{executed_step}', next immediate actions: {next_actions}"
            )
            should_stop = result.should_stop
            #### End of decryped task context - nothing should be done after this point ####

        return params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step=executed_step,
                next_step=next_step,
                next_step_at=next_step_at,
                remaining_steps=remaining_steps,
                error=execution_error,
                should_stop=should_stop,
            ),
            next_iteration_description=next_iteration_description,
            next_iteration_description_metadata=next_iteration_description_metadata,
        ).to_dict(include_default_values=False)

    @staticmethod
    async def _wait_and_trigger_on_priority_actions(
        parsed_inputs: params.AutomationWorkflowInputs, resume_execution_time: float
    ) -> list[dict]:
        delay = max(0, resume_execution_time - time.time())
        if priority_actions := await SCHEDULER.INSTANCE.recv_async(topic="user_actions", timeout_seconds=delay):
            AutomationWorkflow.get_logger(parsed_inputs).info(f"Received user actions: {priority_actions}")
            return priority_actions
        return []

    @staticmethod
    async def _process_pending_priority_actions_and_reschedule(
        parsed_inputs: params.AutomationWorkflowInputs,
        previous_iteration_result: params.AutomationWorkflowIterationResult
    ) -> bool:
        if not previous_iteration_result.next_iteration_description:
            return False
        # In case new priority actions were sent, execute them now.
        # Any action sent to this workflow will be lost if not processed by it.
        latest_iteration_result: params.AutomationWorkflowIterationResult = previous_iteration_result
        while new_priority_actions := await AutomationWorkflow._wait_and_trigger_on_priority_actions(
            parsed_inputs, 0
        ):
            extra_iteration_inputs = AutomationWorkflow._create_next_iteration_inputs(
                parsed_inputs, latest_iteration_result.next_iteration_description, 0,
                latest_iteration_result.next_iteration_description_metadata,
            )
            # execute the iteration on the updated state from last iteration
            raw_iteration_result = await AutomationWorkflow.execute_iteration(extra_iteration_inputs, new_priority_actions)
            # use the new inputs for the next iteration of this loop
            parsed_inputs = params.AutomationWorkflowInputs.from_dict(extra_iteration_inputs)
            latest_iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
            if not AutomationWorkflow._should_continue_workflow(parsed_inputs, latest_iteration_result.progress_status, False):
                return False
            if not latest_iteration_result.next_iteration_description:
                raise errors.WorkflowPriorityActionExecutionError(
                    f"Unexpected error: no next iteration description after processing priority actions: {latest_iteration_result}"
                )
        if latest_iteration_result.progress_status.should_stop:
            AutomationWorkflow.get_logger(parsed_inputs).info(
                f"Stopping workflow, should stop: {latest_iteration_result.progress_status.should_stop}"
            )
        else:
            # successful iteration and a new iteration is required, schedule next iteration, don't return anything
            await AutomationWorkflow._schedule_next_iteration(
                parsed_inputs,
                latest_iteration_result.next_iteration_description,  # type: ignore
                latest_iteration_result.progress_status,
                latest_iteration_result.next_iteration_description_metadata,
            )
        return True

    @staticmethod
    async def _schedule_next_iteration(
        parsed_inputs: params.AutomationWorkflowInputs,
        next_iteration_description: str,
        progress_status: params.ProgressStatus,
        next_iteration_description_metadata: typing.Optional[str] = None,
    ):
        next_execution_time = progress_status.next_step_at or 0
        next_iteration_inputs = AutomationWorkflow._create_next_iteration_inputs(
            parsed_inputs, next_iteration_description, next_execution_time, next_iteration_description_metadata
        )
        delay = next_execution_time - time.time()
        delay_str = f", starting in {delay:.2f} seconds" if delay > 0 else ""
        AutomationWorkflow.get_logger(parsed_inputs).info(
            f"Enqueuing next iteration: next step: {progress_status.next_step}, "
            f"remaining steps: {progress_status.remaining_steps}{delay_str}."
        )
        await SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
            AutomationWorkflow.execute_automation,
            inputs=next_iteration_inputs
        )

    @staticmethod
    def _create_next_iteration_inputs(
        parsed_inputs: params.AutomationWorkflowInputs,
        next_iteration_description: str,
        next_execution_time: float,
        next_iteration_description_metadata: typing.Optional[str] = None,
    ) -> dict:
        # update task.content with the next iteration description containing the automation state
        next_task = parsed_inputs.task
        next_task.content = next_iteration_description
        next_task.content_metadata = next_iteration_description_metadata
        next_execution_time = next_execution_time or 0
        return params.AutomationWorkflowInputs(
            task=parsed_inputs.task, execution_time=next_execution_time
        ).to_dict(include_default_values=False)

    @staticmethod
    def _should_continue_workflow(
        parsed_inputs: params.AutomationWorkflowInputs,
        progress_status: params.ProgressStatus,
        stop_on_error: bool
    ) -> bool:
        if progress_status.error:
            # failed iteration, return global progress where it stopped and exit workflow
            AutomationWorkflow.get_logger(parsed_inputs).error(
                f"Failed iteration: stopping workflow, error: {progress_status.error}. "
                f"Iteration's last step: {progress_status.latest_step}"
            )
            return stop_on_error
        elif progress_status.should_stop:
            AutomationWorkflow.get_logger(parsed_inputs).info(
                f"Workflow stop required: stopping workflow"
            )
            return False
        return True

    @staticmethod
    def _get_actions_summary(actions: list["octobot_flow.entities.AbstractActionDetails"], minimal: bool = False) -> str:
        return ", ".join([action.get_summary(minimal=minimal) for action in actions]) if actions else ""

    @staticmethod
    def get_logger(parsed_inputs: params.AutomationWorkflowInputs) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(
            parsed_inputs.task.name or AutomationWorkflow.__name__
        )
