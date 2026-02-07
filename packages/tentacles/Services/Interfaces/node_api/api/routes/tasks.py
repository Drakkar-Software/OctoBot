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

from typing import Any, List, Tuple
import uuid
from fastapi import APIRouter

from tentacles.Services.Interfaces.node_api.models import Task
from octobot_node.scheduler.api import get_all_tasks, get_task_metrics
from octobot_node.scheduler.tasks import trigger_task

router = APIRouter(tags=["tasks"])

@router.post("/", response_model=Tuple[int, int])
def create_tasks(tasks: List[Task]) -> Tuple[int, int]:
    success_count = 0
    error_count = 0
    for task in tasks:
        is_scheduled = trigger_task(task)
        if is_scheduled:
            success_count += 1
        else:
            error_count += 1
    return success_count, error_count


@router.get("/metrics")
def get_metrics() -> Any:
    return get_task_metrics()

@router.get("/", response_model=List[Task])
def get_tasks(page: int = 1, limit: int = 100) -> Any:
    tasks_data = get_all_tasks()
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_tasks = tasks_data[start_idx:end_idx]
    return paginated_tasks

@router.put("/", response_model=Task)
def update_task(taskId: uuid.UUID, task: Task) -> Any:
    # TODO
    return task

@router.delete("/", response_model=str)
def delete_task(taskId: uuid.UUID) -> str:
    # TODO
    return taskId
