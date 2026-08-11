#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import time

import dbos
import octobot_commons.logging as octobot_commons_logging
import octobot_protocol.models as protocol_models

import octobot_node.constants as node_constants
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks


def _logger():
    return octobot_commons_logging.get_logger("GlobalViewAutomationTrigger")


async def account_has_bound_running_automation(user_id: str, account_id: str) -> bool:
    automation_states = await scheduler_api.get_automation_states(user_id)
    for automation_state in automation_states:
        if automation_state.status != protocol_models.WorkflowStatus.RUNNING:
            continue
        if not automation_state.exchange_account_ids or account_id not in automation_state.exchange_account_ids:
            continue
        return True
    return False


async def trigger_account_automations(
    user_id: str,
    account_id: str,
    changed_order_ids: set[str],
) -> None:
    if not changed_order_ids:
        return
    matching_automations = await _matching_automations(user_id, account_id, changed_order_ids)
    for automation_state in matching_automations:
        await _trigger_automation_and_wait(user_id, automation_state.id)


async def _matching_automations(
    user_id: str,
    account_id: str,
    changed_order_ids: set[str],
) -> list[protocol_models.AutomationState]:
    automation_states = await scheduler_api.get_automation_states(user_id)
    matching_automations: list[protocol_models.AutomationState] = []
    for automation_state in automation_states:
        if automation_state.status != protocol_models.WorkflowStatus.RUNNING:
            continue
        if not automation_state.exchange_account_ids or account_id not in automation_state.exchange_account_ids:
            continue
        automation_order_ids = {
            str(order_summary.id)
            for order_summary in (automation_state.orders or [])
            if order_summary.id
        }
        if automation_order_ids.intersection(changed_order_ids):
            matching_automations.append(automation_state)
    return matching_automations


async def _trigger_automation_and_wait(user_id: str, automation_id: str) -> None:
    import octobot_node.scheduler as scheduler_module

    logger = _logger()
    logger.info(
        "Starting forced automation trigger (automation_id=%s, user_id=%s)",
        automation_id,
        user_id,
    )
    scheduler = scheduler_module.SCHEDULER
    active_workflow_ids_before = await scheduler.resolve_active_automation_workflow_ids_for_parent_id(
        user_id,
        automation_id,
    )
    workflow_id_before = active_workflow_ids_before[0] if active_workflow_ids_before else None
    logger.info(
        "Resolved active workflow before trigger (automation_id=%s, workflow_id=%s)",
        automation_id,
        workflow_id_before,
    )

    await scheduler_tasks.send_forced_trigger_to_active_automation(automation_id, user_id)
    logger.info(
        "Forced trigger sent (automation_id=%s, user_id=%s)",
        automation_id,
        user_id,
    )

    if workflow_id_before is None:
        logger.warning(
            "No active workflow to wait for after forced trigger (automation_id=%s, user_id=%s)",
            automation_id,
            user_id,
        )
        return
    logger.info(
        "Waiting for automation workflow iteration (workflow_id=%s)",
        workflow_id_before,
    )
    await _wait_for_workflow_iteration_success(workflow_id_before)
    logger.info(
        "Finished waiting for automation workflow iteration (workflow_id=%s)",
        workflow_id_before,
    )


async def _wait_for_workflow_iteration_success(workflow_id: str) -> None:
    deadline = time.monotonic() + node_constants.GLOBAL_VIEW_AUTOMATION_TRIGGER_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        workflow_status = await dbos.DBOS.get_workflow_status_async(workflow_id)
        if workflow_status is not None:
            if workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value:
                return
            if workflow_status.status in (
                dbos.WorkflowStatusString.ERROR.value,
                dbos.WorkflowStatusString.CANCELLED.value,
                dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED.value,
            ):
                _logger().error(
                    "Automation workflow %s ended with status %s while waiting for forced trigger iteration",
                    workflow_id,
                    workflow_status.status,
                )
                return
        await asyncio.sleep(
            node_constants.GLOBAL_VIEW_WORKFLOW_POLL_INTERVAL_SECONDS
        )
    _logger().error(
        "Timed out waiting for automation workflow %s to complete forced trigger iteration",
        workflow_id,
    )
