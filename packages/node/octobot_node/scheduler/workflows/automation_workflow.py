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

import octobot_node.models
import octobot_node.scheduler.octobot_lib as octobot_lib
import octobot_node.scheduler.task_context
import octobot_node.scheduler.workflows.base as workflow_base
import octobot_node.scheduler.workflows.params as params
import octobot_node.errors as errors


from octobot_node.scheduler import SCHEDULER  # avoid circular import

if typing.TYPE_CHECKING:
    import mini_octobot.entities


INIT_STEP = "init"


@SCHEDULER.INSTANCE.dbos_class()
class AutomationWorkflow(workflow_base.DBOSWorkflowHelperMixin):
    # use dict as input to parse minimizable dataclasses and facilitate data format updates
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_automation")
    async def execute_automation(t: params.Tracker, inputs: dict) -> typing.Optional[dict]:
        parsed_inputs = params.AutomationWorkflowInputs.from_dict(inputs)
        t.logger.info(
            f"AutomationWorkflow started, delay: {parsed_inputs.delay}, "
            f"next actions: {parsed_inputs.progress_status.next_step if parsed_inputs.progress_status else INIT_STEP}"
        )
        await AutomationWorkflow.sleep_if_needed(t, parsed_inputs.delay)
        global_progress = parsed_inputs.progress_status or params.ProgressStatus()
        raw_iteration_result = await AutomationWorkflow.execute_iteration(t, parsed_inputs.task)
        iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
        # always save progress
        global_progress.update(iteration_result.progress_status)
        if global_progress.error:
            # failed iteration, return global progress where it stopped and exit workflow
            t.logger.error(f"Failed iteration: stopping workflow, error: {global_progress.error}")
            return global_progress.model_dump(exclude_defaults=True)
        if iteration_result.next_iteration_description:
            # successful iteration and a new iteration is required, schedule next iteration, don't return anything
            await AutomationWorkflow._schedule_next_iteration(t, parsed_inputs, global_progress, iteration_result)
        else:
            # successful iteration, no new iteration is required, return global progress and exit workflow
            t.logger.info(
                f"Completed all iterations, global result: "
                f"{global_progress.model_dump_json(exclude_defaults=True)}"
            )
            return global_progress.model_dump(exclude_defaults=True)

    @staticmethod
    async def _schedule_next_iteration(
        t: params.Tracker,
        parsed_inputs: params.AutomationWorkflowInputs,
        global_progress: params.ProgressStatus,
        iteration_result: params.AutomationWorkflowIterationResult
    ):
        new_delay = 0
        parsed_next_iteration_description = octobot_lib.OctoBotActionsJobDescription.from_dict(
            iteration_result.next_iteration_description
        )
        if next_execution_time := parsed_next_iteration_description.get_next_execution_time():
            new_delay = next_execution_time - time.time()
        next_task = parsed_inputs.task
        next_task.content = json.dumps(iteration_result.next_iteration_description)
        t.logger.info(f"Enqueuing next iteration, delay: {new_delay}, next actions: {global_progress.next_step}")
        await SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
            AutomationWorkflow.execute_automation, t=t,
            inputs=params.AutomationWorkflowInputs(
                task=parsed_inputs.task, progress_status=global_progress, delay=new_delay
            ).to_dict(include_default_values=False)
        )

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="execute_iteration")
    async def execute_iteration(t: params.Tracker, task: octobot_node.models.Task) -> dict:
        latest_step_result = {}
        execution_error: typing.Optional[str] = None
        with octobot_node.scheduler.task_context.encrypted_task(task):
            latest_step = INIT_STEP
            if task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
                t.logger.info(f"Executing task '{task.name}' ...")
                result: octobot_lib.OctoBotActionsJobResult = await octobot_lib.OctoBotActionsJob(
                    task.content
                ).run()
                executed_step = ""
                if result.processed_actions:
                    if latest_step := ", ".join([str(action.get_summary()) for action in result.processed_actions]):
                        executed_step = latest_step
                    for action in result.processed_actions:
                        if action.error_status is not None:
                            t.logger.error(
                                f"Error: {action.error_status} when executing action {action.id}: {action.get_summary()} "
                            )
                            execution_error = action.error_status
                latest_step_result = AutomationWorkflow._format_octobot_actions_job_result(result)
            else:
                raise errors.WorkflowInputError(f"Invalid task type: {task.type}")
        next_actions = (
            result.actions_dag.get_executable_actions()
            if result.next_actions_description and result.actions_dag else []
        )
        next_step = ", ".join([action.get_summary() for action in next_actions]) if next_actions else ""
        t.logger.info(
            f"Iteration completed, executed step: '{executed_step}', next immediate actions: {next_actions}"
        )
        remaining_steps = (
            len(result.actions_dag.get_pending_actions()) if result.actions_dag else 0
        )
        new_progress = params.ProgressStatus(
            latest_step=executed_step,
            latest_step_result=latest_step_result,
            next_step=next_step,
            next_step_at=result.next_actions_description.get_next_execution_time() if result.next_actions_description else None,
            remaining_steps=remaining_steps + 1 if result.next_actions_description else (
                1 if result.next_actions_description else 0
            ),
            error=execution_error,
        )
        return params.AutomationWorkflowIterationResult(
            progress_status=new_progress,
            next_iteration_description=result.next_actions_description.to_dict(include_default_values=False) if result.next_actions_description else None,
        ).to_dict(include_default_values=False)

    @staticmethod
    def _format_octobot_actions_job_result(result: octobot_lib.OctoBotActionsJobResult) -> dict:
        result_dict = {
            "orders": result.get_created_orders(),
            "transfers": result.get_deposit_and_withdrawal_details(),
        }
        if failed_actions := result.get_failed_actions():
            result_dict["errors"] = failed_actions
        return result_dict
