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

import dataclasses
import typing
import json
import copy
import time

import octobot_node.models
import octobot_node.enums
import octobot_node.scheduler.octobot_lib as octobot_lib
import octobot_node.scheduler.task_context
import octobot_node.scheduler.workflows.base as workflow_base
import octobot_commons.dataclasses.minimizable_dataclass
import octobot_node.errors as errors


from octobot_node.scheduler import SCHEDULER # avoid circular import


@dataclasses.dataclass
class BotWorkflowInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task: octobot_node.models.Task
    delay: float = 0


@dataclasses.dataclass
class BotIterationResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task_result: dict
    next_iteration_time: typing.Optional[float]
    next_task: typing.Optional[octobot_node.models.Task]


INIT_STEP = "init"


@SCHEDULER.INSTANCE.dbos_class()
class BotWorkflow(workflow_base.DBOSWorkflowHelperMixin):
    # use dict as input to parse minimizable dataclasses and facilitate data format updates

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_octobot")
    async def execute_octobot(t: workflow_base.Tracker, inputs: dict) -> dict:
        parsed_inputs = BotWorkflowInputs.from_dict(inputs)
        should_continue = True
        delay = parsed_inputs.delay
        if delay > 0:
            await workflow_base.DBOSWorkflowHelperMixin.register_delayed_start_step(t, delay, INIT_STEP)
        next_task: octobot_node.models.Task = parsed_inputs.task
        while should_continue:
            await BotWorkflow.sleep_if_needed(t, delay)
            raw_iteration_result = await BotWorkflow.execute_iteration(t, next_task)
            iteration_result = BotIterationResult.from_dict(raw_iteration_result)
            if iteration_result.next_iteration_time:
                should_continue = True
                delay = iteration_result.next_iteration_time - time.time()
                if iteration_result.next_task is None:
                    raise errors.WorkflowInputError(f"iteration_result.next_task is None, this should not happen. {iteration_result=}")
                next_task = iteration_result.next_task
            else:
                should_continue = False
        t.logger.info(f"BotWorkflow completed, last iteration result: {iteration_result.task_result}")
        return iteration_result.task_result

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="execute_iteration")
    async def execute_iteration(t: workflow_base.Tracker, task: octobot_node.models.Task) -> dict:
        next_iteration_time = None
        task_output = {}
        next_task = copy.copy(task)
        with octobot_node.scheduler.task_context.encrypted_task(task):
            current_step = INIT_STEP
            if task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
                t.logger.info(f"Executing task '{task.name}' ...")
                result: octobot_lib.OctoBotActionsJobResult = await octobot_lib.OctoBotActionsJob(
                    task.content
                ).run()
                current_step = ", ".join([str(action.config) for action in result.processed_actions]) if result.processed_actions else None
                task_output = BotWorkflow._format_octobot_actions_job_result(result)
                if result.next_actions_description:
                    next_iteration_time = result.next_actions_description.get_next_execution_time()
                    next_task.content = json.dumps(result.next_actions_description.to_dict(
                        include_default_values=False
                    ))
            else:
                raise errors.WorkflowInputError(f"Invalid task type: {task.type}")
            t.logger.info(
                f"Task '{task.name}' completed. Next immediate actions: "
                f"{result.next_actions_description.immediate_actions if result.next_actions_description else None}"
            )
            await t.set_current_step(workflow_base.ProgressStatus(
                previous_step=current_step,
                previous_step_details=task_output,
                next_step=", ".join([str(action.config) for action in result.next_actions_description.immediate_actions]) if result.next_actions_description else None,
                next_step_at=result.next_actions_description.get_next_execution_time() if result.next_actions_description else None,
                remaining_steps=len(result.next_actions_description.pending_actions) + 1 if result.next_actions_description else (
                    1 if result.next_actions_description else 0
                ),
            ))
        task_result = {
            octobot_node.enums.TaskResultKeys.STATUS.value: octobot_node.models.TaskStatus.COMPLETED.value,
            octobot_node.enums.TaskResultKeys.RESULT.value: task_output,
            octobot_node.enums.TaskResultKeys.METADATA.value: task.result_metadata,
            octobot_node.enums.TaskResultKeys.TASK.value: {"name": task.name},
            octobot_node.enums.TaskResultKeys.ERROR.value: None,
        }
        return BotIterationResult(
            task_result=task_result,
            next_iteration_time=next_iteration_time,
            next_task=next_task,
        ).to_dict(include_default_values=False)

    @staticmethod
    def _format_octobot_actions_job_result(result: octobot_lib.OctoBotActionsJobResult) -> dict:
        return {
            "orders": result.get_created_orders(),
            "transfers": result.get_deposit_and_withdrawal_details(),
        }
