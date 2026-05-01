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
import octobot_flow.entities
import octobot_node.enums
import octobot_node.models
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.workflows.params as params


async def trigger_task(task: octobot_node.models.Task) -> bool:
    import octobot_node.scheduler  # avoid circular import
    if not octobot_node.scheduler.is_initialized():
        raise RuntimeError("Scheduler is not initialized")
    import octobot_node.scheduler.workflows.automation_workflow as automation_workflow
    handle = None
    # enqueue workflow instead of starting it to dispatch them to multiple workers if possible
    if task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
        handle = await octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
            automation_workflow.AutomationWorkflow.execute_automation,
            inputs=params.AutomationWorkflowInputs(task=task).to_dict(include_default_values=False)
        )
    else:
        raise ValueError(f"Unsupported task type: {task.type}")
    return handle is not None


async def send_actions_to_automation(actions: list[dict], automation_id: str):
    import octobot_node.scheduler  # avoid circular import
    workflow_status = await workflows_util.get_automation_workflow_status(automation_id)
    payload = params.AutomationWorkflowActionUpdate(
        actions_type=octobot_node.enums.AutomationWorkflowActionTypes.USER_ACTIONS.value,
        actions_details=actions,
    ).to_dict(include_default_values=False)
    await octobot_node.scheduler.SCHEDULER.INSTANCE.send_async(
        workflow_status.workflow_id,
        payload,
        topic=octobot_node.enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value,
    )


async def trigger_copier_automation(automation_id: str, trading_signal: octobot_flow.entities.TradingSignal) -> None:
    import octobot_node.scheduler  # avoid circular import
    payload = params.AutomationWorkflowActionUpdate(
        actions_type=octobot_node.enums.AutomationWorkflowActionTypes.TRADING_SIGNAL.value,
        actions_details=[trading_signal.to_dict(include_default_values=False)],
    ).to_dict(include_default_values=False)
    await octobot_node.scheduler.SCHEDULER.INSTANCE.send_async(
        automation_id,
        payload,
        topic=octobot_node.enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value,
    )
