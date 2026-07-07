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
import asyncio
import logging
import os
import time
import typing

import dbos
import sqlalchemy

import octobot_node.config
import octobot_node.enums
import octobot_node.scheduler.workflows_util as workflows_util

if typing.TYPE_CHECKING:
    import octobot_node.scheduler.scheduler as scheduler_module

AUTOMATION_EXECUTION_RETENTION_SECONDS = float(
    os.getenv("AUTOMATION_EXECUTION_RETENTION_SECONDS", 60 * 60 * 24 * 2)
)  # 2 days
AUTOMATION_EXECUTIONS_TO_KEEP = 2

_TERMINAL_WORKFLOW_STATUS_VALUES = frozenset(
    workflow_status.value
    for workflow_status in workflows_util.get_user_action_terminal_workflow_statuses()
)

def should_skip_retention_cleanup_on_this_node() -> bool:
    return octobot_node.config.settings.CONSUMER_ONLY


def is_terminal_workflow(workflow_status: dbos.WorkflowStatus) -> bool:
    return workflow_status.status in _TERMINAL_WORKFLOW_STATUS_VALUES


def _retention_cutoff_ms(*, retention_seconds: float, now_ms: int) -> int:
    return now_ms - int(retention_seconds * 1000)


def get_outdated_automation_execution_deletions(
    workflows: list[dbos.WorkflowStatus],
    *,
    retention_seconds: float,
    now_ms: int,
    executions_to_keep: int = AUTOMATION_EXECUTIONS_TO_KEEP,
) -> dict[str, list[str]]:
    deletions_by_automation: dict[str, list[str]] = {}
    cutoff_ms = _retention_cutoff_ms(retention_seconds=retention_seconds, now_ms=now_ms)
    by_parent = workflows_util.get_workflows_by_parent_id(workflows)
    for parent_id, parent_workflows in by_parent.items():
        sorted_workflows = sorted(
            parent_workflows,
            key=workflows_util._automation_child_workflow_sort_key,
            reverse=True,
        )
        protected_ids = {
            workflow_status.workflow_id
            for workflow_status in sorted_workflows[:executions_to_keep]
        }
        parent_deletions: list[str] = []
        for workflow_status in sorted_workflows[executions_to_keep:]:
            if workflow_status.workflow_id in protected_ids:
                continue
            if not is_terminal_workflow(workflow_status):
                continue
            if (workflow_status.updated_at or 0) >= cutoff_ms:
                continue
            parent_deletions.append(workflow_status.workflow_id)
        if parent_deletions:
            deletions_by_automation[parent_id] = parent_deletions
    return deletions_by_automation


def get_outdated_dbos_cleanup_execution_workflow_ids(
    cleanup_workflows: list[dbos.WorkflowStatus],
    *,
    retention_seconds: float,
    now_ms: int,
) -> list[str]:
    cutoff_ms = _retention_cutoff_ms(retention_seconds=retention_seconds, now_ms=now_ms)
    return [
        workflow_status.workflow_id
        for workflow_status in cleanup_workflows
        if is_terminal_workflow(workflow_status)
        and (workflow_status.updated_at or 0) < cutoff_ms
    ]


_TERMINAL_DELETE_WORKFLOW_STATUSES = [
    dbos.WorkflowStatusString.SUCCESS,
    dbos.WorkflowStatusString.ERROR,
    dbos.WorkflowStatusString.CANCELLED,
    dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED,
]


async def get_workflows_to_delete(
    scheduler: "scheduler_module.Scheduler",
    workflow_ids: list[str],
) -> list[str]:
    automation_workflows = await scheduler.get_parent_and_children_automation_workflow_ids(
        None,
        workflow_ids,
        _TERMINAL_DELETE_WORKFLOW_STATUSES,
    )
    user_action_workflows = await scheduler._get_user_action_workflow_ids(
        None,
        workflow_ids,
        _TERMINAL_DELETE_WORKFLOW_STATUSES,
        load_output=True,
    )
    return automation_workflows + user_action_workflows


def vacuum_dbos_system_database(dbos_instance: dbos.DBOS, *, logger: logging.Logger) -> None:
    logger.info("Vacuuming database")
    with dbos_instance._sys_db.engine.begin() as conn:
        conn.execute(sqlalchemy.text("VACUUM"))
    logger.info("Database vacuum completed")


async def delete_workflows_and_vacuum(
    dbos_instance: dbos.DBOS,
    workflow_ids: list[str],
    *,
    logger: logging.Logger,
) -> None:
    logger.info("Deleting %s workflows", len(workflow_ids))
    await dbos_instance.delete_workflows_async(workflow_ids, delete_children=False)
    vacuum_dbos_system_database(dbos_instance, logger=logger)


async def cleanup_outdated_automation_executions(
    scheduler: "scheduler_module.Scheduler",
) -> dict[str, typing.Any]:
    if not scheduler.INSTANCE:
        return {
            "deleted_by_automation": {},
            "deleted_cleanup_executions": 0,
            "total_deleted": 0,
        }
    now_ms = int(time.time() * 1000)
    retention_seconds = AUTOMATION_EXECUTION_RETENTION_SECONDS
    import octobot_node.scheduler.workflows.automation_workflow as automation_workflow
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
    automation_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=automation_workflow.WORKFLOW_NAME,
        queue_name=[octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value],
        load_input=False,
        load_output=False,
    )
    cleanup_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=dbos_cleanup_workflow.WORKFLOW_NAME,
        load_input=False,
        load_output=False,
    )
    deletions_by_automation = get_outdated_automation_execution_deletions(
        automation_workflows,
        retention_seconds=retention_seconds,
        now_ms=now_ms,
    )
    cleanup_execution_ids = get_outdated_dbos_cleanup_execution_workflow_ids(
        cleanup_workflows,
        retention_seconds=retention_seconds,
        now_ms=now_ms,
    )
    automation_execution_ids = [
        workflow_id
        for workflow_ids in deletions_by_automation.values()
        for workflow_id in workflow_ids
    ]
    all_ids_to_delete = automation_execution_ids + cleanup_execution_ids
    summary = {
        "deleted_by_automation": {
            parent_id: len(workflow_ids)
            for parent_id, workflow_ids in deletions_by_automation.items()
        },
        "deleted_cleanup_executions": len(cleanup_execution_ids),
        "total_deleted": len(all_ids_to_delete),
    }
    if all_ids_to_delete:
        scheduler.logger.info(
            "Deleting %s outdated workflow executions: %s automation groups, %s cleanup runs",
            len(all_ids_to_delete),
            len(deletions_by_automation),
            len(cleanup_execution_ids),
        )
        await delete_workflows_and_vacuum(
            scheduler.INSTANCE,
            all_ids_to_delete,
            logger=scheduler.logger,
        )
    scheduler.logger.info("DBOS cleanup summary: %s", summary)
    return summary


def _get_latest_cleanup_execution_timestamp_ms(
    cleanup_workflows: list[dbos.WorkflowStatus],
) -> int:
    if not cleanup_workflows:
        return 0
    workflow_status = cleanup_workflows[0]
    return workflow_status.updated_at or workflow_status.created_at or 0


def _is_cleanup_execution_stale(
    *,
    latest_timestamp_ms: int,
    now_ms: int,
    threshold_seconds: float,
) -> bool:
    if latest_timestamp_ms == 0:
        return True
    return (now_ms - latest_timestamp_ms) > int(threshold_seconds * 1000)


async def _should_trigger_stale_cleanup(scheduler: "scheduler_module.Scheduler") -> bool:
    if should_skip_retention_cleanup_on_this_node():
        return False
    if not scheduler.is_initialized():
        return False
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
    cleanup_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=dbos_cleanup_workflow.WORKFLOW_NAME,
        sort_desc=True,
        limit=1,
        load_input=False,
        load_output=False,
    )
    now_ms = int(time.time() * 1000)
    latest_timestamp_ms = _get_latest_cleanup_execution_timestamp_ms(cleanup_workflows)
    return _is_cleanup_execution_stale(
        latest_timestamp_ms=latest_timestamp_ms,
        now_ms=now_ms,
        threshold_seconds=dbos_cleanup_workflow.STALE_EXECUTION_THRESHOLD_SECONDS,
    )


async def _run_delayed_cleanup_trigger_if_stale(scheduler: "scheduler_module.Scheduler") -> None:
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
    logger = logging.getLogger("workflows_retention")
    logger.info(
        "Scheduling stale dbos_cleanup check in %s seconds",
        dbos_cleanup_workflow.STARTUP_TRIGGER_DELAY_SECONDS,
    )
    await asyncio.sleep(dbos_cleanup_workflow.STARTUP_TRIGGER_DELAY_SECONDS)
    if not scheduler.is_initialized():
        logger.info("Skipping stale dbos_cleanup trigger: scheduler is no longer initialized")
        return
    if not await _should_trigger_stale_cleanup(scheduler):
        logger.info("Skipping stale dbos_cleanup trigger: latest execution is recent enough")
        return
    logger.info("Triggering stale dbos_cleanup schedule %s", dbos_cleanup_workflow.SCHEDULE_NAME)
    dbos.DBOS.trigger_schedule(dbos_cleanup_workflow.SCHEDULE_NAME)


def schedule_startup_cleanup_trigger(scheduler: "scheduler_module.Scheduler") -> None:
    logger = logging.getLogger("workflows_retention")
    if should_skip_retention_cleanup_on_this_node():
        logger.info("Skipping stale dbos_cleanup startup trigger: consumer-only node")
        return
    try:
        event_loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "No running event loop; skipping stale dbos_cleanup startup trigger scheduling",
        )
        return
    scheduler.__class__.STARTUP_CLEANUP_TASK = event_loop.create_task(
        _run_delayed_cleanup_trigger_if_stale(scheduler),
    )


def cancel_startup_cleanup_trigger(scheduler: "scheduler_module.Scheduler") -> None:
    logger = logging.getLogger("workflows_retention")
    startup_cleanup_task = scheduler.__class__.STARTUP_CLEANUP_TASK
    if startup_cleanup_task is not None and not startup_cleanup_task.done():
        startup_cleanup_task.cancel()
        logger.info("Cancelled stale dbos_cleanup startup trigger task")
    scheduler.__class__.STARTUP_CLEANUP_TASK = None
