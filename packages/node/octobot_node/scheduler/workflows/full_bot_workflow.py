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

import octobot_node.models
import octobot_node.enums
import octobot_node.scheduler.workflows.base as workflow_base
import octobot_node.scheduler.task_context

from octobot_node.scheduler import SCHEDULER # avoid circular import
import octobot_commons.dataclasses.minimizable_dataclass


@dataclasses.dataclass
class FullBotWorkflowStartInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task: octobot_node.models.Task
    delay: float

@dataclasses.dataclass
class FullBotWorkflowStopInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task: octobot_node.models.Task
    delay: float


@SCHEDULER.INSTANCE.dbos_class()
class FullBotWorkflow(workflow_base.DBOSWorkflowHelperMixin):
    # use dict as inputs to parse minimizable dataclasses and facilitate data format updates

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="start_full_octobot")
    async def start(t: workflow_base.Tracker, inputs: dict) -> dict:
        parsed_inputs = FullBotWorkflowStartInputs.from_dict(inputs)
        if parsed_inputs.delay > 0:
            await workflow_base.DBOSWorkflowHelperMixin.register_delayed_start_step(t, parsed_inputs.delay, "start_bot")
            await FullBotWorkflow.sleep_if_needed(t, parsed_inputs.delay)
        # todo implement start logic: start bot with process name from self.get_bot_process_name()
        with octobot_node.scheduler.task_context.encrypted_task(parsed_inputs.task):
            parsed_inputs.task.result = "ok"
        return {
            octobot_node.enums.TaskResultKeys.STATUS.value: octobot_node.models.TaskStatus.COMPLETED.value,
            octobot_node.enums.TaskResultKeys.RESULT.value: parsed_inputs.task.result,
            octobot_node.enums.TaskResultKeys.METADATA.value: parsed_inputs.task.result_metadata,
            octobot_node.enums.TaskResultKeys.TASK.value: {"name": parsed_inputs.task.name},
            octobot_node.enums.TaskResultKeys.ERROR.value: None,
        }

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="stop_full_octobot")
    async def stop(t: workflow_base.Tracker, inputs: dict) -> dict:
        parsed_inputs = FullBotWorkflowStopInputs.from_dict(inputs)
        if parsed_inputs.delay > 0:
            await workflow_base.DBOSWorkflowHelperMixin.register_delayed_start_step(t, parsed_inputs.delay, "stop_bot")
            await FullBotWorkflow.sleep_if_needed(t, parsed_inputs.delay)
        # todo implement stop logic: stop bot with process name from self.get_bot_process_name()
        with octobot_node.scheduler.task_context.encrypted_task(parsed_inputs.task):
            parsed_inputs.task.result = "ok"
        return {
            octobot_node.enums.TaskResultKeys.STATUS.value: octobot_node.models.TaskStatus.COMPLETED.value,
            octobot_node.enums.TaskResultKeys.RESULT.value: parsed_inputs.task.result,
            octobot_node.enums.TaskResultKeys.METADATA.value: parsed_inputs.task.result_metadata,
            octobot_node.enums.TaskResultKeys.TASK.value: {"name": parsed_inputs.task.name},
            octobot_node.enums.TaskResultKeys.ERROR.value: None,
        }

    @staticmethod
    def get_bot_process_name(t: workflow_base.Tracker) -> str:
        return f"octobot_{t.name}"
