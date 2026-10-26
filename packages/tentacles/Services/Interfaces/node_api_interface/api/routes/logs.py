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
import logging
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
# Active log file (no ``.log.N`` rotation suffix).
_ACTIVE_LOG_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+\.log$")
# OctoBot fileFormatter: asctime then levelname within the first columns of each line.
_LOG_HEADER_SEARCH_WINDOW = 48
_LOG_LEVEL_TOKENS = tuple(
    sorted(
        (
            logging.getLevelName(level)
            for level in (
                logging.CRITICAL,
                logging.ERROR,
                logging.WARNING,
                logging.INFO,
                logging.DEBUG,
            )
        ),
        key=len,
        reverse=True,
    )
)
_VALID_TIMING_PREFIX_RE = re.compile(r"^[\d\-: ]+$")


class ExportLogsRequest(BaseModel):
    task_ids: list[str] | None = None
    latest_only: bool = False
    remove_timing: bool = False


def _split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def _find_log_level_start(line_body: str) -> int | None:
    window = line_body[:_LOG_HEADER_SEARCH_WINDOW]
    best_pos: int | None = None
    for level in _LOG_LEVEL_TOKENS:
        pos = window.find(level)
        if pos == -1:
            continue
        before_ok = pos == 0 or window[pos - 1] == " "
        after_end = pos + len(level)
        after_ok = after_end < len(window) and window[after_end] == " "
        if before_ok and after_ok and (best_pos is None or pos < best_pos):
            best_pos = pos
    if best_pos is None:
        return None
    prefix = line_body[:best_pos].strip()
    if not prefix or not _VALID_TIMING_PREFIX_RE.match(prefix):
        return None
    return best_pos


def strip_log_line_timings(text: str) -> str:
    """Replace leading asctime on standard log header lines with per-file sequence numbers."""
    sequence = 0
    result_parts: list[str] = []
    for line in text.splitlines(keepends=True):
        line_body, line_end = _split_line_ending(line)
        level_start = _find_log_level_start(line_body)
        if level_start is not None:
            sequence += 1
            result_parts.append(f"{sequence} {line_body[level_start:]}{line_end}")
        else:
            result_parts.append(line)
    return "".join(result_parts)


def _build_zip_from_log_files(
    log_entries: list[tuple[str, str]], *, remove_timing: bool = False
) -> bytes | None:
    """Zip existing files. Each entry is ``(absolute path, archive name)``; missing paths are skipped."""
    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for log_path, arcname in log_entries:
            if os.path.isfile(log_path):
                if remove_timing:
                    with open(log_path, encoding="utf-8") as log_file:
                        content = strip_log_line_timings(log_file.read())
                    archive.writestr(arcname, content)
                else:
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


def _collect_latest_task_log_entries(task_id: str) -> list[tuple[str, str]]:
    """Active ``.log`` files for one automation (flat file and/or folder tree)."""
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
                if not _ACTIVE_LOG_NAME_RE.match(filename):
                    continue
                if not _SAFE_MAIN_LOG_NAME_RE.match(filename):
                    continue
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


def build_logs_zip(
    task_ids: list[str], *, latest_only: bool = False, remove_timing: bool = False
) -> bytes | None:
    """Zip per-automation logs for the given task ids.

    When ``latest_only`` is False, includes ``AUTOMATION_LOGS_FOLDER/<id>.log`` when
    present and, for process automations, all files under ``AUTOMATION_LOGS_FOLDER/<id>/``.

    When ``latest_only`` is True, includes only active ``.log`` files (no ``.log.N``
    backups) from the flat path and/or automation folder for each id.

    Missing files or folders are skipped. Returns None when nothing was found.
    """
    log_entries: list[tuple[str, str]] = []
    collector = (
        _collect_latest_task_log_entries if latest_only else _collect_task_log_entries
    )
    for task_id in task_ids:
        log_entries.extend(collector(task_id))
    return _build_zip_from_log_files(log_entries, remove_timing=remove_timing)


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
    if body.latest_only and not body.task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="task_ids required when latest_only is true",
        )
    archive = build_logs_zip(
        body.task_ids,
        latest_only=body.latest_only,
        remove_timing=body.remove_timing,
    )
    if archive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found for the selected OctoBots",
        )
    return fastapi.Response(content=archive, media_type="application/zip")
