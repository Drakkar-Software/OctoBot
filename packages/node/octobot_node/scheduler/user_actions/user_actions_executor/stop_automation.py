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

import octobot_protocol.models as protocol_models

import octobot_node.enums as node_enums
import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation_user_action_executor as automation_user_action_executor
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.workflows.params as workflow_params


def _get_stop_automation_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.StopAutomationConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete stop-automation configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.StopAutomationConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"StopAutomationActionExecutor expected StopAutomationConfiguration, got {type(payload).__name__}"
        )
    return payload


def _stop_priority_action_dict(*, user_action: protocol_models.UserAction) -> list[dict]:
    return [
        {
            "id": f"action_stop_priority_{user_action.id}",
            "dsl_script": "stop_automation()",
        }
    ]


class StopAutomationActionExecutor(automation_user_action_executor.AutomationUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        if not scheduler_module.is_initialized():
            raise RuntimeError("Scheduler is not initialized")

        stop_payload = _get_stop_automation_payload(user_action)
        scheduler = scheduler_module.SCHEDULER
        matching_workflow_ids = await scheduler.resolve_active_automation_workflow_ids_for_parent_id(
            self._wallet_address,
            stop_payload.id,
        )
        if not matching_workflow_ids:
            raise node_errors.ActiveAutomationWorkflowNotFoundError(
                f"No active automation workflow for parent id {stop_payload.id!r} "
                f"(wallet_address={self._wallet_address!r})."
            )
        if len(matching_workflow_ids) > 1:
            raise node_errors.AmbiguousActiveAutomationWorkflowError(
                f"Expected exactly one active automation workflow for parent id {stop_payload.id!r}, "
                f"got {len(matching_workflow_ids)}: {matching_workflow_ids!r} "
                f"(wallet_address={self._wallet_address!r})."
            )

        target_workflow_id = matching_workflow_ids[0]
        actions_details = _stop_priority_action_dict(user_action=user_action)
        payload = workflow_params.AutomationWorkflowActionUpdate(
            actions_type=node_enums.AutomationWorkflowActionTypes.USER_ACTIONS.value,
            actions_details=actions_details,
        ).to_dict(include_default_values=False)
        await scheduler.INSTANCE.send_async(
            target_workflow_id,
            payload,
            topic=node_enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value,
        )
        self._mark_user_action_completed(user_action)
