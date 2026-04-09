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
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.api
import octobot_node.scheduler.tasks

router = APIRouter(tags=["tasks"])

@router.post("/", response_model=tuple[int, int])
async def create_tasks(tasks: list[octobot_node.models.Task]) -> tuple[int, int]:
    success_count = 0
    error_count = 0
    for task in tasks:
        is_scheduled = await octobot_node.scheduler.tasks.trigger_task(task)
        if is_scheduled:
            success_count += 1
        else:
            error_count += 1
    return success_count, error_count


class EncryptContentRequest(BaseModel):
    contents: list[str]


class EncryptedItem(BaseModel):
    content: str
    content_metadata: str


@router.post("/encrypt-content", response_model=list[EncryptedItem])
def encrypt_content(request: EncryptContentRequest) -> list[EncryptedItem]:
    if not octobot_node.config.settings.is_node_side_encryption_enabled:
        raise HTTPException(status_code=400, detail="Encryption is not enabled")
    from octobot_node.scheduler.encryption.task_inputs import encrypt_task_content
    results = []
    for content in request.contents:
        encrypted_content, metadata = encrypt_task_content(content)
        results.append(EncryptedItem(content=encrypted_content, content_metadata=metadata))
    return results


@router.get("/metrics")
async def get_metrics() -> typing.Any:
    return await octobot_node.scheduler.api.get_task_metrics()

@router.get("/", response_model=list[octobot_node.models.Task])
async def get_tasks(page: int = 1, limit: int = 100) -> typing.Any:
    tasks_data = await octobot_node.scheduler.api.get_all_tasks()
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_tasks = tasks_data[start_idx:end_idx]
    return paginated_tasks

@router.put("/", response_model=octobot_node.models.Task)
def update_task(taskId: uuid.UUID, task: octobot_node.models.Task) -> typing.Any:
    # TODO
    return task

@router.delete("/", response_model=str)
async def delete_task(taskId: uuid.UUID) -> str:
    try:
        await octobot_node.scheduler.api.delete_task(str(taskId))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return str(taskId)
