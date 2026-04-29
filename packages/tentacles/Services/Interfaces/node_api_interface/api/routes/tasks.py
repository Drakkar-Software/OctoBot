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
from fastapi import APIRouter, HTTPException, Query
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


@router.get("/server-public-keys")
def get_server_public_keys() -> dict:
    if not octobot_node.config.settings.is_node_side_encryption_enabled:
        raise HTTPException(status_code=400, detail="Server encryption keys not configured")
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    rsa_private = load_pem_private_key(octobot_node.config.settings.TASKS_SERVER_RSA_PRIVATE_KEY, password=None)
    ecdsa_private = load_pem_private_key(octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY, password=None)
    return {
        "server_rsa_public_pem": rsa_private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(),
        "server_ecdsa_public_pem": ecdsa_private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(),
    }


@router.get("/metrics")
async def get_metrics() -> typing.Any:
    return await octobot_node.scheduler.api.get_task_metrics()

@router.get("/", response_model=list[octobot_node.models.Task], response_model_exclude_none=True)
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

@router.delete("/", response_model=list[str])
async def delete_tasks(taskIds: list[uuid.UUID] = Query(...)) -> list[str]:
    try:
        return await octobot_node.scheduler.api.delete_tasks([str(t) for t in taskIds])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
