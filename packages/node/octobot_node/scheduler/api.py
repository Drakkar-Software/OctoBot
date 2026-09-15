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

import asyncio
import typing
import uuid

import dbos
import octobot_commons.logging as octobot_commons_logging
import octobot_protocol.models as protocol_models

import octobot_node.config
import octobot_node.constants
import octobot_node.models
import octobot_node.scheduler
import octobot_node.scheduler.workflows_util as workflows_util

logger = octobot_commons_logging.get_logger("scheduler_api")


def get_node_status() -> dict[str, str | int | None | uuid.UUID]:
    consumer_running = (
        octobot_node.scheduler.SCHEDULER.INSTANCE
        and octobot_node.scheduler.SCHEDULER.INSTANCE._launched
    )
    is_running = octobot_node.config.settings.IS_MASTER_MODE or bool(consumer_running)
    status = "running" if is_running else "stopped"

    backend_type = "postgres" if octobot_node.config.settings.SCHEDULER_POSTGRES_URL else "sqlite"
    workers = 1

    if octobot_node.config.settings.IS_MASTER_MODE:
        node_type = "both"
    elif octobot_node.config.settings.CONSUMER_ONLY:
        node_type = "consumer"
    else:
        # no worker should run
        node_type = "none"
        workers = 0

    return {
        "node_type": node_type,
        "backend_type": backend_type,
        "workers": workers,
        "status": status,
        "redis_url": None,
        "sqlite_file": octobot_node.config.settings.SCHEDULER_SQLITE_FILE if not octobot_node.config.settings.SCHEDULER_POSTGRES_URL else None,
    }


async def get_automation_states(
    user_id: typing.Optional[str],
    statuses: typing.Optional[list[dbos.WorkflowStatusString]] = None,
) -> list[protocol_models.AutomationState]:
    return await octobot_node.scheduler.SCHEDULER.get_automation_states(user_id, statuses)


async def list_user_actions(user_id: typing.Optional[str], active_only: bool) -> list[protocol_models.UserAction]:
    return await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id, active_only)


async def get_task_metrics(
    user_id: typing.Optional[str] = None,
) -> dict[str, int]:
    scheduler = octobot_node.scheduler.SCHEDULER
    if not scheduler.INSTANCE:
        return {"pending": 0, "scheduled": 0, "results": 0}
    try:
        pending_statuses, result_statuses = await asyncio.gather(
            scheduler.INSTANCE.list_workflows_async(status=[
                dbos.WorkflowStatusString.ENQUEUED.value,
                dbos.WorkflowStatusString.PENDING.value,
            ], load_output=False),
            scheduler.INSTANCE.list_workflows_async(status=[
                dbos.WorkflowStatusString.SUCCESS.value,
                dbos.WorkflowStatusString.ERROR.value,
            ], load_output=False),
        )
        if user_id is not None:
            automation_queue = octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value
            pending_only_automation = [
                row for row in (pending_statuses or []) if row.queue_name == automation_queue
            ]
            result_only_automation = [
                row for row in (result_statuses or []) if row.queue_name == automation_queue
            ]
            pending_statuses = workflows_util.filter_by_wallet(
                pending_only_automation,
                user_id,
                octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE,
            )
            result_statuses = workflows_util.filter_by_wallet(
                result_only_automation,
                user_id,
                octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE,
            )
        return {
            "pending": len(pending_statuses or []),
            "scheduled": 0,
            "results": len(result_statuses or []),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve task metrics from scheduler: {e}")
        return {"pending": 0, "scheduled": 0, "results": 0}


def _get_active_execution(
    executions: list[octobot_node.models.Execution],
) -> typing.Optional[octobot_node.models.Execution]:
    pending = [e for e in executions if e.status == octobot_node.models.TaskStatus.PENDING]
    if pending:
        return pending[-1]
    dated = sorted(
        [e for e in executions if e.completed_at is not None],
        key=lambda e: e.completed_at,
    )
    return dated[-1] if dated else (executions[-1] if executions else None)


def _build_tasks_from_executions(
    executions: list[octobot_node.models.Execution],
) -> list[octobot_node.models.Task]:
    grouped: dict[str, list[octobot_node.models.Execution]] = {}
    for execution in executions:
        parent_id = execution.id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
        grouped.setdefault(parent_id, []).append(execution)

    tasks = []
    for parent_id, group in grouped.items():
        active = _get_active_execution(group)
        active_name = active.name if active else None
        active_content = active.actions if active else None
        error = active.error if active else None
        active_wallet = active.user_id if active else None
        is_encrypted = any(e.is_encrypted for e in group)
        for execution in group:
            execution.name = None
            if active is None or execution.id != active.id:
                execution.result_metadata = None
        tasks.append(octobot_node.models.Task(
            id=parent_id,
            name=active_name,
            content=active_content,
            is_encrypted=is_encrypted,
            executions=group,
            error=error,
            user_id=active_wallet,
        ))
    return tasks


async def _enrich_tasks_with_child_octobot_process(
    tasks: list[octobot_node.models.Task],
    user_id: typing.Optional[str],
) -> None:
    active_task_statuses = {
        octobot_node.models.TaskStatus.PENDING,
        octobot_node.models.TaskStatus.RUNNING,
        octobot_node.models.TaskStatus.SCHEDULED,
        octobot_node.models.TaskStatus.PERIODIC,
    }
    active_task_ids = {
        task.id
        for task in tasks
        if task.id is not None
        and (active_execution := _get_active_execution(task.executions)) is not None
        and active_execution.status in active_task_statuses
    }
    if not active_task_ids:
        return
    try:
        automation_states = await octobot_node.scheduler.SCHEDULER.get_automation_states(
            user_id,
            statuses=[
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
        )
        child_process_by_automation_id = {
            automation_state.id: automation_state.child_octobot_process
            for automation_state in automation_states
            if automation_state.child_octobot_process is not None
            and automation_state.id in active_task_ids
        }
        for task in tasks:
            if task.id in child_process_by_automation_id:
                if task.metadata is None:
                    task.metadata = octobot_node.models.TaskMetadata()
                task.metadata.child_octobot_process = child_process_by_automation_id[task.id]
    except Exception as enrich_error:
        logger.exception(
            enrich_error, True, "Failed to enrich tasks with child_octobot_process: %s", enrich_error
        )


async def get_all_tasks(
    user_id: typing.Optional[str] = None,
) -> list[octobot_node.models.Task]:
    executions: list[octobot_node.models.Execution] = []
    try:
        periodic, pending, scheduled, results = await asyncio.gather(
            octobot_node.scheduler.SCHEDULER.get_periodic_tasks(user_id=user_id),
            octobot_node.scheduler.SCHEDULER.get_pending_tasks(user_id=user_id),
            octobot_node.scheduler.SCHEDULER.get_scheduled_tasks(user_id=user_id),
            octobot_node.scheduler.SCHEDULER.get_results(user_id=user_id),
        )
        executions.extend(periodic)
        executions.extend(pending)
        executions.extend(scheduled)
        executions.extend(results)
    except Exception as e:
        logger.error("Failed to retrieve tasks from scheduler: %s", e)
        return []

    tasks = _build_tasks_from_executions(executions)
    await _enrich_tasks_with_child_octobot_process(tasks, user_id)
    logger.debug("Returning %d total tasks from %d executions", len(tasks), len(executions))
    return tasks


async def get_tasks_export_results(
    task_ids: list[str],
    user_id: typing.Optional[str],
    user_rsa_public_key: typing.Optional[str] = None,
) -> dict[str, dict[str, str]]:
    if not task_ids:
        return {}
    return await octobot_node.scheduler.SCHEDULER.get_workflows_export_results(
        task_ids, user_id, user_rsa_public_key=user_rsa_public_key
    )


async def delete_tasks(task_ids: list[str]) -> list[str]:
    await octobot_node.scheduler.SCHEDULER.delete_workflows(task_ids)
    return task_ids


async def cancel_tasks(task_ids: list[str]) -> list[str]:
    return await octobot_node.scheduler.SCHEDULER.cancel_workflows(task_ids)


async def retrieve_workflow_handle(workflow_id: str):
    return await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)


async def await_workflow_result_from_id(workflow_id: str) -> typing.Any:
    workflow_handle = await retrieve_workflow_handle(workflow_id)
    return await asyncio.wait_for(
        workflow_handle.get_result(),
        timeout=octobot_node.constants.USER_ACTION_WORKFLOW_RESULT_TIMEOUT_SECONDS,
    )


async def get_task_result(task_id: str):
    try:
        handle = await retrieve_workflow_handle(task_id)
    except Exception:
        return {"error": "task not found"}

    try:
        status = await handle.get_status()
        if status is None:
            return {"error": "task not found"}
        wf_status = getattr(status, "status", None) or getattr(status, "workflow_status", None)
        if wf_status == "SUCCESS":
            result_data = await handle.get_result()
            return {"status": "completed", "data": result_data}
        if wf_status == "ERROR":
            try:
                result_data = await handle.get_result()
            except Exception as error:
                result_data = {"error": str(error)}
            return {"status": "completed", "data": result_data}
    except Exception as error:
        logger.debug(f"Workflow {task_id} not yet complete: {error}")
    return {"status": "pending or running"}
