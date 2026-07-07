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

import pydantic
from fastapi import APIRouter, HTTPException, status

import octobot_node.errors as node_errors
import octobot_node.scheduler
import octobot_node.scheduler.generic_process_octobot as generic_process_octobot_module

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser  # type: ignore[no-redef]
    from tentacles.Services.Interfaces.node_api_interface.api.user_id import evm_to_user_id  # type: ignore[no-redef]
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]
    from api.user_id import evm_to_user_id  # type: ignore[no-redef]

router = APIRouter(tags=["octobots"])


class CreateGenericProcessBotRequest(pydantic.BaseModel):
    name: str


class CreateGenericProcessBotResponse(pydantic.BaseModel):
    automation_id: str


@router.post(
    "/generic-process",
    response_model=CreateGenericProcessBotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_generic_process_bot(
    body: CreateGenericProcessBotRequest,
    current_user: CurrentUser,
) -> CreateGenericProcessBotResponse:
    if not octobot_node.scheduler.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized",
        )
    bot_name = body.name.strip()
    if not bot_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name must not be empty",
        )
    user_id = evm_to_user_id(current_user.email)
    try:
        automation_id = await generic_process_octobot_module.create_generic_process_bot(user_id, bot_name)
    except node_errors.UserActionError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except TimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out waiting for bot creation workflow",
        ) from error
    return CreateGenericProcessBotResponse(automation_id=automation_id)
