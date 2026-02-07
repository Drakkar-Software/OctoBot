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

import logging
import uuid
from typing import Any

from octobot_node.config import settings
from octobot_node.scheduler import SCHEDULER, CONSUMER

logger = logging.getLogger(__name__)


def get_node_status() -> dict[str, str | int | None | uuid.UUID]:
    consumer_running = CONSUMER.is_started() # TODO use: CONSUMER.is_running()
    is_running = settings.IS_MASTER_MODE or consumer_running
    status = "running" if is_running else "stopped"

    backend_type = "redis" if settings.SCHEDULER_REDIS_URL else "sqlite"
    workers = CONSUMER.workers if settings.SCHEDULER_WORKERS > 0 else None

    if settings.IS_MASTER_MODE and settings.SCHEDULER_WORKERS > 0:
        node_type = "both"
    elif settings.IS_MASTER_MODE:
        node_type = "master"
    elif settings.SCHEDULER_WORKERS > 0:
        node_type = "consumer"
    else:
        node_type = "none"

    return {
        "node_type": node_type,
        "backend_type": backend_type,
        "workers": workers,
        "status": status,
        "redis_url": str(settings.SCHEDULER_REDIS_URL) if settings.SCHEDULER_REDIS_URL else None,
        "sqlite_file": settings.SCHEDULER_SQLITE_FILE if not settings.SCHEDULER_REDIS_URL else None,
    }


def get_task_metrics() -> dict[str, int]:
    try:
        huey_instance = SCHEDULER.INSTANCE
        if huey_instance is None:
            logger.warning("Scheduler instance not initialized")
            return {"pending": 0, "scheduled": 0, "results": 0}

        scheduled_count = huey_instance.scheduled_count()
        periodic_tasks = SCHEDULER.get_periodic_tasks()
        scheduled_count += len(periodic_tasks)

        return {
            "pending": huey_instance.pending_count(),
            "scheduled": scheduled_count,
            "results": huey_instance.result_count(),
        }
    except Exception as e:
        logger.error("Failed to retrieve task metrics from scheduler: %s", e)
        return {"pending": 0, "scheduled": 0, "results": 0}


def get_all_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    try:
        periodic_tasks = SCHEDULER.get_periodic_tasks()
        tasks.extend(periodic_tasks)

        pending_tasks = SCHEDULER.get_pending_tasks()
        tasks.extend(pending_tasks)

        scheduled_tasks = SCHEDULER.get_scheduled_tasks()
        tasks.extend(scheduled_tasks)

        results = SCHEDULER.get_results()
        tasks.extend(results)
    except Exception as e:
        logger.error("Failed to retrieve tasks from scheduler: %s", e)

    logger.debug("Returning %d total tasks", len(tasks))
    return tasks


async def get_task_result(task_id: str):
    res = SCHEDULER.INSTANCE.result(task_id)

    if res is None:
        return {"error": "task not found"}

    # True if finished
    if res.ready():          
        # blocks if not ready, or returns the value                        
        result_data = res.get()
        return {"status": "completed", "data": result_data}
    else:
        return {"status": "pending or running"}
