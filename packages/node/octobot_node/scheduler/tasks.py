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
import typing

import octobot_flow.entities
import octobot_node.enums
import octobot_node.models
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.workflows.params as params
import octobot_protocol.models as protocol_models


async def trigger_user_action_workflow(
    user_action: protocol_models.UserAction,
    wallet_address: str,
) -> str:
    import octobot_node.scheduler  # avoid circular import
    if not octobot_node.scheduler.is_initialized():
        raise RuntimeError("Scheduler is not initialized")
    import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow
    handle = await octobot_node.scheduler.SCHEDULER.USER_ACTION_QUEUE.enqueue_async(
        user_action_workflow.UserActionWorkflow.execute_user_action,
        inputs=params.UserActionWorkflowInputs(
            wallet_address=wallet_address, user_action=user_action,
        ).to_dict(include_default_values=False)
    )
    return handle.workflow_id

async def trigger_task(
    task: octobot_node.models.Task, target_workflow_id: typing.Optional[str] = None
) -> str:
    import octobot_node.scheduler  # avoid circular import
    if not octobot_node.scheduler.is_initialized():
        raise RuntimeError("Scheduler is not initialized")
    import octobot_node.scheduler.workflows.automation_workflow as automation_workflow
    handle = None
    # enqueue workflow instead of starting it to dispatch them to multiple workers if possible
    if task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
        inputs = params.AutomationWorkflowInputs(task=task).to_dict(include_default_values=False)
        if target_workflow_id:
            with octobot_node.scheduler.SCHEDULER.SetWorkflowID(target_workflow_id):
                handle = await octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
                    automation_workflow.AutomationWorkflow.execute_automation,
                    inputs=inputs
                )
        else:
            handle = await octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
                automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs
            )
    else:
        raise ValueError(f"Unsupported task type: {task.type}")
    return handle.workflow_id


async def send_actions_to_automation(actions: list[dict], automation_id: str):
    workflow_status = await workflows_util.get_automation_workflow_status(automation_id)
    await send_actions_to_automation_workflow(actions, workflow_status.workflow_id)


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


async def send_forced_trigger_to_automation(automation_id: str):
    workflow_status = await workflows_util.get_automation_workflow_status(automation_id)
    await send_forced_trigger_to_automation_workflow(workflow_status.workflow_id)


async def _send_automation_workflow_action_update(
    target_workflow_id: str,
    actions_type: str,
    actions_details: list[dict],
) -> None:
    import octobot_node.scheduler  # avoid circular import
    payload = params.AutomationWorkflowActionUpdate(
        actions_type=actions_type,
        actions_details=actions_details,
    ).to_dict(include_default_values=False)
    await octobot_node.scheduler.SCHEDULER.INSTANCE.send_async(
        target_workflow_id,
        payload,
        topic=octobot_node.enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value,
    )


async def send_actions_to_automation_workflow(actions: list[dict], target_workflow_id: str) -> None:
    await _send_automation_workflow_action_update(
        target_workflow_id,
        octobot_node.enums.AutomationWorkflowActionTypes.USER_ACTIONS.value,
        actions,
    )


async def send_forced_trigger_to_automation_workflow(target_workflow_id: str) -> None:
    await _send_automation_workflow_action_update(
        target_workflow_id,
        octobot_node.enums.AutomationWorkflowActionTypes.FORCED_TRIGGER.value,
        [],
    )
