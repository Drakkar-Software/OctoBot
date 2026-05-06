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
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

import octobot_commons.logging as logging
import octobot_node.config
import octobot_node.models
import octobot_node.scheduler
import octobot_node.scheduler.api
import octobot_node.scheduler.tasks

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser  # type: ignore[no-redef]
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]

router = APIRouter(tags=["tasks"])
logger = logging.get_logger(__name__)

_MAX_PAGE_LIMIT = 500


@router.post("/", response_model=tuple[int, int])
async def create_tasks(
    tasks: list[octobot_node.models.Task],
    current_user: CurrentUser,
) -> tuple[int, int]:
    if not octobot_node.scheduler.is_initialized():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Scheduler not initialized")
    success_count = 0
    error_count = 0
    for task in tasks:
        task.wallet_address = current_user.email
        is_scheduled = await octobot_node.scheduler.tasks.trigger_task(task)
        if is_scheduled:
            success_count += 1
        else:
            error_count += 1
    return success_count, error_count


@router.get("/server-public-keys")
def get_server_public_keys(current_user: CurrentUser) -> dict:
    if not octobot_node.config.settings.is_node_side_encryption_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server encryption keys not configured")
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    rsa_private = load_pem_private_key(octobot_node.config.settings.TASKS_SERVER_RSA_PRIVATE_KEY, password=None)
    ecdsa_private = load_pem_private_key(octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY, password=None)
    return {
        "server_rsa_public_pem": rsa_private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(),
        "server_ecdsa_public_pem": ecdsa_private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(),
    }


@router.get("/metrics")
async def get_metrics(current_user: CurrentUser) -> typing.Any:
    wallet_filter = None if current_user.is_superuser else current_user.email
    return await octobot_node.scheduler.api.get_task_metrics(wallet_address=wallet_filter)


@router.get("/", response_model=list[octobot_node.models.Task], response_model_exclude_none=True)
async def get_tasks(
    current_user: CurrentUser,
    page: int = 1,
    limit: int = 100,
) -> typing.Any:
    limit = max(1, min(limit, _MAX_PAGE_LIMIT))
    wallet_filter = None if current_user.is_superuser else current_user.email
    tasks_data = await octobot_node.scheduler.api.get_all_tasks(wallet_address=wallet_filter)

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    return tasks_data[start_idx:end_idx]


@router.put("/", response_model=octobot_node.models.Task)
def update_task(current_user: CurrentUser, taskId: uuid.UUID, task: octobot_node.models.Task) -> typing.Any:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


class ExportResultsBody(BaseModel):
    task_ids: list[str]
    user_rsa_public_key: str | None = None


@router.post("/export-results", response_model=dict[str, dict[str, str]])
async def export_results(body: ExportResultsBody, current_user: CurrentUser) -> dict[str, dict[str, str]]:
    """Batch-decrypt completed task results for export. One round-trip for all selected tasks."""
    wallet_filter = None if current_user.is_superuser else current_user.email
    return await octobot_node.scheduler.api.get_tasks_export_results(
        body.task_ids, wallet_filter, user_rsa_public_key=body.user_rsa_public_key
    )


@router.delete("/", response_model=list[str])
async def delete_tasks(
    current_user: CurrentUser,
    taskIds: list[uuid.UUID] = Query(...),
) -> list[str]:
    requested_ids = [str(t) for t in taskIds]
    if not current_user.is_superuser:
        # Ownership check: only allow deleting own tasks
        owned_tasks = await octobot_node.scheduler.api.get_all_tasks(wallet_address=current_user.email)
        owned_ids = {t.id for t in owned_tasks if t.id is not None}
        unauthorized = [tid for tid in requested_ids if tid not in owned_ids]
        if unauthorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to delete tasks: {unauthorized}",
            )
    try:
        return await octobot_node.scheduler.api.delete_tasks(requested_ids)
    except ValueError as e:
        logger.exception(e, True, "delete_tasks failed")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


class CancelTasksBody(BaseModel):
    task_ids: list[str]


@router.post("/cancel", response_model=list[str])
async def cancel_tasks(
    body: CancelTasksBody,
    current_user: CurrentUser,
) -> list[str]:
    if not current_user.is_superuser:
        owned_tasks = await octobot_node.scheduler.api.get_all_tasks(wallet_address=current_user.email)
        owned_ids = {t.id for t in owned_tasks if t.id is not None}
        unauthorized = [tid for tid in body.task_ids if tid not in owned_ids]
        if unauthorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to cancel tasks: {unauthorized}",
            )
    try:
        return await octobot_node.scheduler.api.cancel_tasks(body.task_ids)
    except ValueError as e:
        logger.exception(e, True, "cancel_tasks failed")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
