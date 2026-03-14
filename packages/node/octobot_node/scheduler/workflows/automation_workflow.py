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
import typing
import json
import time
import dbos as dbos_lib

import octobot_commons.logging

import octobot_node.models
import octobot_node.scheduler.octobot_lib as octobot_lib
import octobot_node.scheduler.task_context
import octobot_node.scheduler.workflows.params as params
import octobot_node.errors as errors


from octobot_node.scheduler import SCHEDULER  # avoid circular import



@SCHEDULER.INSTANCE.dbos_class()
class AutomationWorkflow:
    # Always use dict as input to parse minimizable dataclasses and facilitate data format updates

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_automation")
    async def execute_automation(inputs: dict) -> None:
        parsed_inputs = params.AutomationWorkflowInputs.from_dict(inputs)
        delay_str = f" with {parsed_inputs.delay} initial delay" if parsed_inputs.delay > 0 else ""
        AutomationWorkflow.get_logger(parsed_inputs).info(f"{AutomationWorkflow.__name__} started{delay_str}.")
        if parsed_inputs.delay > 0:
            AutomationWorkflow.get_logger(parsed_inputs).info(f"Sleeping for {parsed_inputs.delay} seconds ...")
            await dbos_lib.DBOS.sleep_async(parsed_inputs.delay)
        raw_iteration_result = await AutomationWorkflow.execute_iteration(inputs)
        iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
        if iteration_result.progress_status.error:
            # failed iteration, return global progress where it stopped and exit workflow
            AutomationWorkflow.get_logger(parsed_inputs).error(
                f"Failed iteration: stopping workflow, error: {iteration_result.progress_status.error}. "
                f"Iteration: {iteration_result.progress_status.latest_step}"
            )
            return
        if iteration_result.next_iteration_description:
            # successful iteration and a new iteration is required, schedule next iteration, don't return anything
            await AutomationWorkflow._schedule_next_iteration(parsed_inputs, iteration_result)
        else:
            # successful iteration, no new iteration is required, exit workflow
            AutomationWorkflow.get_logger(parsed_inputs).info(f"Completed all iterations, stopping workflow")

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="execute_iteration")
    async def execute_iteration(inputs: dict) -> dict:
        parsed_inputs: params.AutomationWorkflowInputs = params.AutomationWorkflowInputs.from_dict(inputs)
        execution_error: typing.Optional[str] = None
        executed_step: str = "no action executed"
        result: octobot_lib.OctoBotActionsJobResult = None # type: ignore
        with octobot_node.scheduler.task_context.encrypted_task(parsed_inputs.task):
            if parsed_inputs.task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
                AutomationWorkflow.get_logger(parsed_inputs).info(f"Executing task '{parsed_inputs.task.name}' ...")
                result = await octobot_lib.OctoBotActionsJob(
                    parsed_inputs.task.content
                ).run()
                if result.processed_actions:
                    if latest_step := ", ".join([str(action.get_summary()) for action in result.processed_actions]):
                        executed_step = latest_step
                    for action in result.processed_actions:
                        if action.error_status is not None:
                            AutomationWorkflow.get_logger(parsed_inputs).error(
                                f"Error: {action.error_status} when executing action {action.id}: {action.get_summary()} "
                            )
                            execution_error = action.error_status
            if result is None:
                raise errors.WorkflowInputError(f"Invalid task type: {parsed_inputs.task.type}")
        next_actions = (
            result.actions_dag.get_executable_actions()
            if result.next_actions_description and result.actions_dag else []
        )
        next_step = ", ".join([action.get_summary() for action in next_actions]) if next_actions else ""
        AutomationWorkflow.get_logger(parsed_inputs).info(
            f"Iteration completed, executed step: '{executed_step}', next immediate actions: {next_actions}"
        )
        remaining_steps = (
            len(result.actions_dag.get_pending_actions()) if result.actions_dag else 0
        )
        progress = params.ProgressStatus(
            latest_step=executed_step,
            next_step=next_step,
            next_step_at=result.next_actions_description.get_next_execution_time() if result.next_actions_description else None,
            remaining_steps=remaining_steps + 1 if result.next_actions_description else (
                1 if result.next_actions_description else 0
            ),
            error=execution_error,
        )
        return params.AutomationWorkflowIterationResult(
            progress_status=progress,
            next_iteration_description=(
                result.next_actions_description.to_dict(include_default_values=False)
                if result.next_actions_description else None
            )
        ).to_dict(include_default_values=False)

    @staticmethod
    async def _schedule_next_iteration(
        parsed_inputs: params.AutomationWorkflowInputs,
        iteration_result: params.AutomationWorkflowIterationResult
    ):
        new_delay = 0
        if next_execution_time := iteration_result.progress_status.next_step_at:
            new_delay = next_execution_time - time.time()
        # update task.content with the next iteration description containing the automation state
        next_task = parsed_inputs.task
        next_task.content = json.dumps(iteration_result.next_iteration_description)
        delay_str = f", starting in {new_delay} seconds" if new_delay > 0 else ""
        AutomationWorkflow.get_logger(parsed_inputs).info(
            f"Enqueuing next iteration: next step: {iteration_result.progress_status.next_step}, "
            f"remaining steps: {iteration_result.progress_status.remaining_steps}{delay_str}."
        )
        await SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
            AutomationWorkflow.execute_automation,
            inputs=params.AutomationWorkflowInputs(
                task=parsed_inputs.task, delay=new_delay
            ).to_dict(include_default_values=False)
        )

    @staticmethod
    def get_logger(parsed_inputs: params.AutomationWorkflowInputs) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(
            parsed_inputs.task.name or AutomationWorkflow.__name__
        )
