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
import re
import tempfile
import typing

import pydantic
from fastapi import APIRouter, HTTPException, status

import octobot_commons.logging as logging
import octobot_node.constants as node_constants
import octobot.community.errors_upload.error_sharing as error_sharing

try:
    from api.deps import CurrentUser
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser

router = APIRouter(tags=["logs"])

logger = logging.get_logger(__name__)

# Only alphanumeric characters, hyphens, and underscores are valid in automation IDs.
# This prevents path traversal attacks when ids are interpolated into file paths.
_SAFE_AUTOMATION_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


class ShareLogsRequest(pydantic.BaseModel):
    automation_ids: typing.Optional[list[str]] = None


@router.post("/share")
async def share_logs(
    current_user: CurrentUser,
    body: typing.Optional[ShareLogsRequest] = None,
) -> typing.Any:
    export_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
            export_path = tmp.name
        log_paths = None
        if body and body.automation_ids:
            for automation_id in body.automation_ids:
                if not _SAFE_AUTOMATION_ID_RE.match(automation_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid automation_id",
                    )
            log_paths = [
                os.path.join(node_constants.AUTOMATION_LOGS_FOLDER, f"{automation_id}.log")
                for automation_id in body.automation_ids
            ]
        result = await error_sharing.share_logs(export_path, log_paths)
        if result is None:
            return {"success": False, "error": "Not connected to octobot.cloud"}
        return {
            "success": True,
            "errorId": result.get("errorId"),
            "errorSecret": result.get("errorSecret"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e, True, "Error sharing logs")
        return {"success": False, "error": "Failed to share logs"}
    finally:
        if export_path is not None:
            try:
                os.unlink(export_path)
            except OSError:
                pass
