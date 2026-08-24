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
import datetime
import os
import pathlib
import time
import typing

import dbos
import sqlalchemy

import octobot_commons.logging as logging
import octobot_node.config
import octobot_node.enums
import octobot_node.scheduler.workflows_util as workflows_util

if typing.TYPE_CHECKING:
    import octobot_node.scheduler.scheduler as scheduler_module

_GIBIBYTE = 1024 ** 3

AUTOMATION_EXECUTION_RETENTION_SECONDS = float(
    os.getenv("AUTOMATION_EXECUTION_RETENTION_SECONDS", 60 * 60 * 24 * 2)
)  # 2 days
AUTOMATION_EXECUTIONS_TO_KEEP = 2

DBOS_CLEANUP_SIZE_TIER_1_BYTES = int(
    os.getenv("DBOS_CLEANUP_SIZE_TIER_1_BYTES", str(1 * _GIBIBYTE))
)
DBOS_CLEANUP_SIZE_TIER_2_BYTES = int(
    os.getenv("DBOS_CLEANUP_SIZE_TIER_2_BYTES", str(3 * _GIBIBYTE))
)
DBOS_CLEANUP_CRON_DAILY = os.getenv("DBOS_CLEANUP_CRON_DAILY", "0 0 * * *")
DBOS_CLEANUP_CRON_12H = os.getenv("DBOS_CLEANUP_CRON_12H", "0 */12 * * *")
DBOS_CLEANUP_CRON_6H = os.getenv("DBOS_CLEANUP_CRON_6H", "0 */6 * * *")

EMPTY_CLEANUP_SUMMARY: dict[str, typing.Any] = {
    "deleted_by_automation": {},
    "deleted_cleanup_executions": 0,
    "deleted_global_view_executions": 0,
    "deleted_portfolio_history_executions": 0,
    "total_deleted": 0,
}

_TERMINAL_WORKFLOW_STATUS_VALUES = frozenset(
    workflow_status.value
    for workflow_status in workflows_util.get_user_action_terminal_workflow_statuses()
)

def should_skip_retention_cleanup_on_this_node() -> bool:
    return octobot_node.config.settings.CONSUMER_ONLY


def is_terminal_workflow(workflow_status: dbos.WorkflowStatus) -> bool:
    status = (
        workflow_status["status"]
        if isinstance(workflow_status, dict)
        else workflow_status.status
    )
    return status in _TERMINAL_WORKFLOW_STATUS_VALUES


def _retention_cutoff_ms(*, retention_seconds: float, now_ms: int) -> int:
    return now_ms - int(retention_seconds * 1000)


def get_outdated_terminal_workflow_ids(
    workflows: list[dbos.WorkflowStatus],
    *,
    retention_seconds: float,
    now_ms: int,
) -> list[str]:
    cutoff_ms = _retention_cutoff_ms(retention_seconds=retention_seconds, now_ms=now_ms)
    return [
        workflow_status.workflow_id
        for workflow_status in workflows
        if is_terminal_workflow(workflow_status)
        and (workflow_status.updated_at or 0) < cutoff_ms
    ]


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
    return get_outdated_terminal_workflow_ids(
        cleanup_workflows,
        retention_seconds=retention_seconds,
        now_ms=now_ms,
    )


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


def get_scheduler_database_size_bytes(dbos_instance: dbos.DBOS) -> int | None:
    if octobot_node.config.settings.SCHEDULER_POSTGRES_URL:
        return _get_postgres_database_size_bytes(dbos_instance)
    return _get_sqlite_database_size_bytes()


def select_cleanup_cron_for_database_size(database_size_bytes: int | None) -> str:
    if database_size_bytes is None:
        return DBOS_CLEANUP_CRON_DAILY
    if database_size_bytes < DBOS_CLEANUP_SIZE_TIER_1_BYTES:
        return DBOS_CLEANUP_CRON_DAILY
    if database_size_bytes < DBOS_CLEANUP_SIZE_TIER_2_BYTES:
        return DBOS_CLEANUP_CRON_12H
    return DBOS_CLEANUP_CRON_6H


def vacuum_dbos_system_database(dbos_instance: dbos.DBOS) -> None:
    logger = _get_logger()
    logger.info("Vacuuming database")
    with dbos_instance._sys_db.engine.begin() as conn:
        conn.execute(sqlalchemy.text("VACUUM"))
    logger.info("Database vacuum completed")


async def delete_workflows(
    dbos_instance: dbos.DBOS,
    workflow_ids: list[str],
) -> None:
    _get_logger().info("Deleting %s workflows", len(workflow_ids))
    await dbos_instance.delete_workflows_async(workflow_ids, delete_children=False)


async def delete_workflows_and_vacuum(
    dbos_instance: dbos.DBOS,
    workflow_ids: list[str]
) -> None:
    await delete_workflows(dbos_instance, workflow_ids)
    vacuum_dbos_system_database(dbos_instance)


async def cleanup_outdated_automation_executions(
    scheduler: "scheduler_module.Scheduler",
) -> dict[str, typing.Any]:
    if not scheduler.INSTANCE:
        _get_logger().warning("Scheduler not initialized, skipping cleanup")
        return dict(EMPTY_CLEANUP_SUMMARY)
    now_ms = int(time.time() * 1000)
    retention_seconds = AUTOMATION_EXECUTION_RETENTION_SECONDS
    import octobot_node.scheduler.workflows.automation_workflow as automation_workflow
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
    import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow
    import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow
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
    global_view_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=global_view_workflow.WORKFLOW_NAME,
        queue_name=[octobot_node.enums.SchedulerQueues.GLOBAL_VIEW_QUEUE.value],
        load_input=False,
        load_output=False,
    )
    portfolio_history_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=portfolio_history_workflow.WORKFLOW_NAME,
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
    global_view_execution_ids = get_outdated_terminal_workflow_ids(
        global_view_workflows,
        retention_seconds=retention_seconds,
        now_ms=now_ms,
    )
    portfolio_history_execution_ids = get_outdated_terminal_workflow_ids(
        portfolio_history_workflows,
        retention_seconds=retention_seconds,
        now_ms=now_ms,
    )
    automation_execution_ids = [
        workflow_id
        for workflow_ids in deletions_by_automation.values()
        for workflow_id in workflow_ids
    ]
    all_ids_to_delete = (
        automation_execution_ids
        + cleanup_execution_ids
        + global_view_execution_ids
        + portfolio_history_execution_ids
    )
    summary = {
        "deleted_by_automation": {
            parent_id: len(workflow_ids)
            for parent_id, workflow_ids in deletions_by_automation.items()
        },
        "deleted_cleanup_executions": len(cleanup_execution_ids),
        "deleted_global_view_executions": len(global_view_execution_ids),
        "deleted_portfolio_history_executions": len(portfolio_history_execution_ids),
        "total_deleted": len(all_ids_to_delete),
    }
    if all_ids_to_delete:
        _get_logger().info(
            "Deleting %s outdated workflow executions: %s automation groups, %s cleanup runs, "
            "%s global view runs, %s portfolio history runs",
            len(all_ids_to_delete),
            len(deletions_by_automation),
            len(cleanup_execution_ids),
            len(global_view_execution_ids),
            len(portfolio_history_execution_ids),
        )
        await delete_workflows(
            scheduler.INSTANCE,
            all_ids_to_delete,
        )
    _get_logger().info("DBOS cleanup summary: %s", summary)
    return summary


async def finalize_dbos_cleanup_run(
    scheduler: "scheduler_module.Scheduler",
    summary: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    if not scheduler.INSTANCE:
        return summary
    database_size_bytes = get_scheduler_database_size_bytes(scheduler.INSTANCE)
    finalized_summary = dict(summary)
    finalized_summary["database_size_bytes"] = database_size_bytes
    total_deleted = finalized_summary.get("total_deleted", 0)
    if total_deleted > 0 or (
        database_size_bytes is not None
        and database_size_bytes >= DBOS_CLEANUP_SIZE_TIER_2_BYTES
    ):
        vacuum_dbos_system_database(scheduler.INSTANCE)
    desired_cron = select_cleanup_cron_for_database_size(database_size_bytes)
    finalized_summary["cleanup_schedule_cron"] = desired_cron
    import octobot_node.scheduler.schedules as schedules_module
    schedule_update = await schedules_module.update_cleanup_schedule_cron(
        scheduler,
        desired_cron,
    )
    finalized_summary["cleanup_schedule_updated"] = schedule_update["changed"]
    _get_logger().info("DBOS cleanup finalized summary: %s", finalized_summary)
    return finalized_summary


def _get_latest_completed_cleanup_timestamp_ms(
    cleanup_workflows: list[dbos.WorkflowStatus],
) -> int:
    if not cleanup_workflows:
        return 0
    workflow_status = cleanup_workflows[0]
    return workflow_status.updated_at or workflow_status.created_at or 0


async def should_skip_retention_cleanup_for_scheduled_time(
    scheduler: "scheduler_module.Scheduler",
    scheduled_time: datetime.datetime,
) -> bool:
    if not scheduler.is_initialized():
        return True
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
    cleanup_workflows = await scheduler.INSTANCE.list_workflows_async(
        name=dbos_cleanup_workflow.WORKFLOW_NAME,
        status=[dbos.WorkflowStatusString.SUCCESS.value],
        sort_desc=True,
        limit=1,
        load_input=False,
        load_output=False,
    )
    latest_timestamp_ms = _get_latest_completed_cleanup_timestamp_ms(cleanup_workflows)
    if latest_timestamp_ms == 0:
        return False
    scheduled_timestamp_ms = int(scheduled_time.timestamp() * 1000)
    return latest_timestamp_ms > scheduled_timestamp_ms


def _get_sqlite_database_size_bytes() -> int | None:
    sqlite_path = pathlib.Path(octobot_node.config.settings.SCHEDULER_SQLITE_FILE)
    if not sqlite_path.is_file():
        missing_file_error = FileNotFoundError(f"Scheduler sqlite file not found: {sqlite_path}")
        _get_logger().exception(
            missing_file_error,
            True,
            "Scheduler sqlite file not found: %s",
            sqlite_path,
        )
        return None
    total_size_bytes = sqlite_path.stat().st_size
    for suffix in ("-wal", "-shm"):
        sidecar_path = pathlib.Path(f"{sqlite_path}{suffix}")
        if sidecar_path.is_file():
            total_size_bytes += sidecar_path.stat().st_size
    return total_size_bytes


def _get_postgres_database_size_bytes(dbos_instance: dbos.DBOS) -> int | None:
    try:
        with dbos_instance._sys_db.engine.begin() as connection:
            database_size = connection.execute(
                sqlalchemy.text("SELECT pg_database_size(current_database())"),
            ).scalar()
        if database_size is None:
            return None
        return int(database_size)
    except Exception as error:
        _get_logger().exception(
            error,
            True,
            "Failed to read postgres database size: %s",
            error,
        )
        return None


def _get_logger() -> logging.BotLogger:
    return logging.get_logger("workflows_retention")
