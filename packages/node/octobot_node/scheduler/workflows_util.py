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
import uuid
import typing
import dbos as dbos_lib

import octobot_node.models as models
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler


async def get_workflow_handle(workflow_id: str) -> dbos_lib.WorkflowHandleAsync:
    return await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)


def generate_workflow_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


async def get_progress_status(workflow_id: str) -> typing.Optional[params.ProgressStatus]:
    workflow_status = await dbos_lib.DBOS.get_workflow_status_async(workflow_id)
    if inputs := get_automation_workflow_inputs(workflow_status):
        return inputs.progress_status
    return None


def get_input_task(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[models.Task]:
    if inputs := get_automation_workflow_inputs(workflow_status):
        return inputs.task
    return None


def get_automation_workflow_inputs(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[params.AutomationWorkflowInputs]:
    for input in list(workflow_status.input.get("args", [])) + list(workflow_status.input.get("kwargs", {}).values()):
        if isinstance(input, dict):
            try:
                parsed_inputs = params.AutomationWorkflowInputs.from_dict(input)
                return parsed_inputs
            except TypeError:
                print(f"Failed to parse inputs: {input}")
                pass
    return None
