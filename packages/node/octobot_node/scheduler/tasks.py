#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import uuid
import octobot_node.models
import octobot_node.scheduler.workflows.base as workflow_base
import octobot_commons.dataclasses.minimizable_dataclass as minimizable_dataclass
from octobot_node.scheduler import SCHEDULER # avoid circular import


def _generate_instance_name() -> str:
    # names can't be re-used: ensure each are unique not to mix
    # workflow attributes on recovery
    return str(uuid.uuid4())


async def trigger_task(task: octobot_node.models.Task) -> bool:
    import octobot_node.scheduler.workflows.bot_workflow as bot_workflow
    import octobot_node.scheduler.workflows.full_bot_workflow as full_bot_workflow
    delay = 1
    handle = None
    # enqueue workflow instead of starting it to dispatch them to multiple workers if possible
    if task.type == octobot_node.models.TaskType.START_OCTOBOT.value:
        handle = await SCHEDULER.BOT_WORKFLOW_QUEUE.enqueue_async(
            full_bot_workflow.FullBotWorkflow.start,
            t=workflow_base.Tracker(name=f"{task.name}_{_generate_instance_name()}"),
            inputs=full_bot_workflow.FullBotWorkflowStartInputs(task=task, delay=delay).to_dict(include_default_values=False)
        )
    elif task.type == octobot_node.models.TaskType.STOP_OCTOBOT.value:
        handle = await SCHEDULER.BOT_WORKFLOW_QUEUE.enqueue_async(
            full_bot_workflow.FullBotWorkflow.stop,
            t=workflow_base.Tracker(name=f"{task.name}_{_generate_instance_name()}"),
            inputs=full_bot_workflow.FullBotWorkflowStopInputs(task=task, delay=delay).to_dict(include_default_values=False)
        )
    elif task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
        handle = await SCHEDULER.BOT_WORKFLOW_QUEUE.enqueue_async(
            bot_workflow.BotWorkflow.execute_octobot,
            t=workflow_base.Tracker(name=f"{task.name}_{_generate_instance_name()}"),
            inputs=bot_workflow.BotWorkflowInputs(task=task, delay=delay).to_dict(include_default_values=False)
        )
    else:
        raise ValueError(f"Invalid task type: {task.type}")
    return handle is not None
