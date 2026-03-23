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
import logging
import typing
import uuid

import octobot_node.config
import octobot_node.constants
import octobot_node.models
import octobot_node.scheduler

logger = logging.getLogger(__name__)


def get_node_status() -> dict[str, str | int | None | uuid.UUID]:
    consumer_running = (
        octobot_node.scheduler.SCHEDULER.INSTANCE 
        and octobot_node.scheduler.SCHEDULER.INSTANCE._launched
    )
    is_running = octobot_node.config.settings.IS_MASTER_MODE or consumer_running
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


async def get_task_metrics() -> dict[str, int]:
    try:
        instance = octobot_node.scheduler.SCHEDULER.INSTANCE
        if instance is None:
            logger.warning("Scheduler instance not initialized")
            pending, completed, periodic = [], [], []
        else:
            pending, completed, periodic = await asyncio.gather(
                instance.list_workflows_async(status=["ENQUEUED", "PENDING"]),
                instance.list_workflows_async(status=["SUCCESS", "ERROR"]),
                octobot_node.scheduler.SCHEDULER.get_periodic_tasks()
            )
        return {
            "pending": len(pending),
            "scheduled": len(periodic),
            "results": len(completed),
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
        tasks.append(octobot_node.models.Task(
            id=parent_id,
            name=active.name if active else None,
            content=active.actions if active else None,
            executions=group,
        ))
    return tasks


async def get_all_tasks() -> list[octobot_node.models.Task]:
    executions: list[octobot_node.models.Execution] = []
    try:
        periodic, pending, scheduled, results = await asyncio.gather(
            octobot_node.scheduler.SCHEDULER.get_periodic_tasks(),
            octobot_node.scheduler.SCHEDULER.get_pending_tasks(),
            octobot_node.scheduler.SCHEDULER.get_scheduled_tasks(),
            octobot_node.scheduler.SCHEDULER.get_results(),
        )
        executions.extend(periodic)
        executions.extend(pending)
        executions.extend(scheduled)
        executions.extend(results)
    except Exception as e:
        logger.error("Failed to retrieve tasks from scheduler: %s", e)
        return []

    tasks = _build_tasks_from_executions(executions)
    logger.debug("Returning %d total tasks from %d executions", len(tasks), len(executions))
    return tasks


async def get_task_result(task_id: str):
    try:
        handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(task_id)
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
            except Exception as e:
                result_data = {"error": str(e)}
            return {"status": "completed", "data": result_data}
    except Exception as e:
        logger.debug(f"Workflow {task_id} not yet complete: {e}")
    return {"status": "pending or running"}
