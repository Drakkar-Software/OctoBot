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

import io
import os
import re
import zipfile

import fastapi
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import octobot_node.constants

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]

router = APIRouter(tags=["logs"])

# Only allow ids that map safely to a "<id>.log" file name (path-traversal guard).
_SAFE_TASK_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class ExportLogsRequest(BaseModel):
    task_ids: list[str]


def build_logs_zip(task_ids: list[str]) -> bytes | None:
    """Zip the per-OctoBot log files (``AUTOMATION_LOGS_FOLDER/<id>.log``) for the given task ids.

    Missing files are skipped. Returns the zip bytes, or None when none of the ids had a log file.
    """
    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for task_id in task_ids:
            log_path = os.path.join(
                octobot_node.constants.AUTOMATION_LOGS_FOLDER, f"{task_id}.log"
            )
            if os.path.isfile(log_path):
                archive.write(log_path, arcname=f"{task_id}.log")
                written += 1
    if written == 0:
        return None
    return buffer.getvalue()


@router.post("/export")
def export_logs(body: ExportLogsRequest, current_user: CurrentUser) -> fastapi.Response:
    for task_id in body.task_ids:
        if not _SAFE_TASK_ID_RE.match(task_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id"
            )
    archive = build_logs_zip(body.task_ids)
    if archive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found for the selected OctoBots",
        )
    return fastapi.Response(content=archive, media_type="application/zip")
