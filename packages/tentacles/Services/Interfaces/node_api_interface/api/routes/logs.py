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
# Top-level log files in BASE_LOGS_FOLDER (no subdirectories), including RotatingFileHandler backups.
_SAFE_MAIN_LOG_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+\.log(\.\d+)?$")


class ExportLogsRequest(BaseModel):
    task_ids: list[str] | None = None


def _build_zip_from_log_files(log_entries: list[tuple[str, str]]) -> bytes | None:
    """Zip existing files. Each entry is ``(absolute path, archive name)``; missing paths are skipped."""
    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for log_path, arcname in log_entries:
            if os.path.isfile(log_path):
                archive.write(log_path, arcname=arcname)
                written += 1
    if written == 0:
        return None
    return buffer.getvalue()


def build_main_logs_zip() -> bytes | None:
    """Zip ``.log`` and rotated ``.log.N`` files directly under ``BASE_LOGS_FOLDER`` (subfolders excluded)."""
    logs_folder = octobot_node.constants.BASE_LOGS_FOLDER
    if not os.path.isdir(logs_folder):
        return None
    log_entries: list[tuple[str, str]] = []
    for entry_name in os.listdir(logs_folder):
        if not _SAFE_MAIN_LOG_NAME_RE.match(entry_name):
            continue
        log_path = os.path.join(logs_folder, entry_name)
        if not os.path.isfile(log_path):
            continue
        log_entries.append((log_path, entry_name))
    return _build_zip_from_log_files(log_entries)


def _is_path_under_root(path: str, root: str) -> bool:
    try:
        return os.path.commonpath(
            [os.path.realpath(path), os.path.realpath(root)]
        ) == os.path.realpath(root)
    except ValueError:
        return False


def _collect_task_log_entries(task_id: str) -> list[tuple[str, str]]:
    logs_root = octobot_node.constants.AUTOMATION_LOGS_FOLDER
    entries: list[tuple[str, str]] = []

    log_file_path = os.path.join(logs_root, f"{task_id}.log")
    if os.path.isfile(log_file_path):
        entries.append((log_file_path, f"{task_id}.log"))

    log_dir_path = os.path.join(logs_root, task_id)
    if os.path.isdir(log_dir_path):
        log_dir_real = os.path.realpath(log_dir_path)
        for dirpath, _dirnames, filenames in os.walk(log_dir_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if not os.path.isfile(file_path):
                    continue
                file_real = os.path.realpath(file_path)
                if not _is_path_under_root(file_real, log_dir_real):
                    continue
                rel_path = os.path.relpath(file_real, logs_root)
                arcname = rel_path.replace(os.sep, "/")
                entries.append((file_real, arcname))

    return entries


def build_logs_zip(task_ids: list[str]) -> bytes | None:
    """Zip per-automation logs for the given task ids.

    Includes ``AUTOMATION_LOGS_FOLDER/<id>.log`` when present and, for process
    automations, all files under ``AUTOMATION_LOGS_FOLDER/<id>/``.

    Missing files or folders are skipped. Returns None when nothing was found.
    """
    log_entries: list[tuple[str, str]] = []
    for task_id in task_ids:
        log_entries.extend(_collect_task_log_entries(task_id))
    return _build_zip_from_log_files(log_entries)


@router.post("/export")
def export_logs(body: ExportLogsRequest, current_user: CurrentUser) -> fastapi.Response:
    if body.task_ids is None:
        archive = build_main_logs_zip()
        if archive is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No logs found in the node logs folder",
            )
        return fastapi.Response(content=archive, media_type="application/zip")
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
