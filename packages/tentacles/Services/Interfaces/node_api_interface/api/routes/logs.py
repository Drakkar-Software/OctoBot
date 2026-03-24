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

import os
import tempfile
import typing

import pydantic
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials

import octobot_node.constants as node_constants
import octobot.community.errors_upload.error_sharing as error_sharing

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser, security_basic
except ImportError:
    from api.deps import CurrentUser, security_basic

router = APIRouter(tags=["logs"])


class ShareLogsRequest(pydantic.BaseModel):
    automation_ids: typing.Optional[list[str]] = None


@router.post("/share")
async def share_logs(
    current_user: CurrentUser,
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
    body: typing.Optional[ShareLogsRequest] = None,
) -> typing.Any:
    try:
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
            export_path = tmp.name
        passphrase = credentials.password if credentials else None
        log_paths = None
        if body and body.automation_ids:
            log_paths = [
                os.path.join(node_constants.AUTOMATION_LOGS_FOLDER, f"{automation_id}.log")
                for automation_id in body.automation_ids
            ]
        result = await error_sharing.share_logs(export_path, passphrase, log_paths)
        if result is None:
            return {"success": False, "error": "Not connected to octobot.cloud"}
        return {
            "success": True,
            "errorId": result.get("errorId"),
            "errorSecret": result.get("errorSecret"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
