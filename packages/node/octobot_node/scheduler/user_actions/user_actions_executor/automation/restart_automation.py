#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import json

import octobot_flow.entities as flow_entities
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.models as models
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.task_context as task_context
import octobot_node.scheduler.user_actions.user_actions_executor.automation.automation_user_action_executor as automation_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
import octobot_node.scheduler.workflows_util as workflows_util


def _get_restart_automation_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.RestartAutomationConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete restart-automation configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.RestartAutomationConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"RestartAutomationActionExecutor expected RestartAutomationConfiguration, "
            f"got {type(payload).__name__}"
        )
    return payload


def _resolve_restart_reset_target_action_id(
    automation_state: flow_entities.AutomationState,
) -> str:
    actions_dag = automation_state.automation.actions_dag
    for action in reversed(actions_dag.actions):
        if action.id == action_details_factory._ACTION_ID_INIT:
            continue
        if isinstance(action, flow_entities.ConfiguredActionDetails):
            if action.action == flow_enums.ActionType.APPLY_CONFIGURATION.value:
                continue
            if not action.can_be_reset():
                continue
        elif not action.can_be_reset():
            continue
        return action.id
    raise node_errors.UnrestartableAutomationError(
        "No resettable automation action found in the latest execution state."
    )


def prepare_automation_state_for_restart(
    automation_state: flow_entities.AutomationState,
) -> flow_entities.AutomationState:
    automation_state.automation.post_actions.stop_automation = False
    automation_state.automation.execution.execution_error = None
    reset_target_action_id = _resolve_restart_reset_target_action_id(automation_state)
    automation_state.automation.actions_dag.reset_to(reset_target_action_id)
    return automation_state


def _task_content_json_from_prepared_state(
    automation_state: flow_entities.AutomationState,
) -> str:
    return json.dumps({"state": automation_state.to_dict(include_default_values=False)})


class RestartAutomationActionExecutor(automation_user_action_executor.AutomationUserActionExecutor):
    async def _id_binds_to_user_action(self, restart_id: str) -> bool:
        listed_user_actions = await scheduler_module.SCHEDULER.list_user_actions(
            self._user_id,
            active_only=False,
        )
        user_action_ids = {user_action.id for user_action in listed_user_actions}
        return restart_id in user_action_ids

    async def _assert_automation_not_running(self, parent_automation_id: str) -> None:
        active_workflow_ids = await scheduler_module.SCHEDULER.resolve_active_automation_workflow_ids_for_parent_id(
            self._user_id,
            parent_automation_id,
        )
        if active_workflow_ids:
            raise node_errors.UnrestartableAutomationError(
                f"Automation {parent_automation_id!r} is still running "
                f"(active workflows: {active_workflow_ids!r})."
            )

    async def _build_restart_task(self, parent_automation_id: str) -> models.Task:
        latest_workflow = (
            await scheduler_module.SCHEDULER.resolve_latest_terminal_automation_workflow_for_parent_id(
                self._user_id,
                parent_automation_id,
            )
        )
        if latest_workflow is None:
            raise node_errors.UnrestartableAutomationError(
                f"No prior terminal execution found for automation {parent_automation_id!r}."
            )
        workflow_output = workflows_util.parse_automation_workflow_output(latest_workflow)
        if workflow_output is None or not workflow_output.state:
            raise node_errors.UnrestartableAutomationError(
                f"Latest execution for automation {parent_automation_id!r} has no usable output state."
            )
        input_task = workflows_util.get_automation_input_task(latest_workflow)
        task_name = input_task.name if input_task is not None else None
        with task_context.encrypted_task(
            models.Task(
                content=workflow_output.state,
                content_metadata=workflow_output.state_metadata,
            )
        ):
            automation_state_dict = automation_states_loader.get_automation_dict(workflow_output.state)[
                automation_states_loader.STATE_KEY
            ]
            automation_state = flow_entities.AutomationState.from_dict(automation_state_dict)
            prepared_state = prepare_automation_state_for_restart(automation_state)
            task_content = _task_content_json_from_prepared_state(prepared_state)
        try:
            next_workflow_id = workflows_util.build_next_child_automation_workflow_id(
                latest_workflow.workflow_id
            )
        except ValueError as error:
            raise node_errors.UnrestartableAutomationError(
                f"Cannot derive restart workflow id from latest execution "
                f"{latest_workflow.workflow_id!r}: {error}"
            ) from error
        return models.Task(
            id=next_workflow_id,
            name=task_name,
            content=task_content,
            content_metadata=workflow_output.state_metadata,
            type=models.TaskType.EXECUTE_ACTIONS.value,
            user_id=self._user_id,
        )

    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        if not scheduler_module.is_initialized():
            raise RuntimeError("Scheduler is not initialized")

        restart_payload = _get_restart_automation_payload(user_action)
        parent_automation_id = workflows_util.normalize_parent_automation_id(restart_payload.id)
        if await self._id_binds_to_user_action(restart_payload.id):
            raise node_errors.UnrestartableAutomationError(
                f"Restart id {restart_payload.id!r} binds to a user action and cannot be restarted."
            )
        await self._assert_automation_not_running(parent_automation_id)
        restart_task = await self._build_restart_task(parent_automation_id)
        self.post_actions.to_create_automation_task = restart_task
        self._mark_user_action_completed(
            user_action,
            created_automation_id=parent_automation_id,
        )
