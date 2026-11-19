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

import base64
import io
import zipfile

import mock

import octobot_node.constants

try:
    from tentacles.Services.Interfaces.node_api_interface.api.routes.logs import (
        build_logs_zip,
        build_main_logs_zip,
        strip_log_line_timings,
    )
except ImportError:
    from api.routes.logs import (  # type: ignore[no-redef]
        build_logs_zip,
        build_main_logs_zip,
        strip_log_line_timings,
    )

_SAMPLE_INFO_LINE = (
    "2026-08-26 10:08:50 INFO   OctoBot Launcher     logger.py:79       "
    "Saving logs in 'logs' folder"
)
_SAMPLE_WARNING_LINE = (
    "2026-08-26 10:08:51 WARNING Configuration        logging_util.py:226      "
    "Profile non-trading from config.json is not available yet"
)

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE, TENANT_ADDRESS


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _assert_auth_error_response(response, expected_code: str) -> None:
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == expected_code


class TestStripLogLineTimings:
    def test_strips_real_shaped_info_line(self):
        result = strip_log_line_timings(_SAMPLE_INFO_LINE + "\n")
        assert result.startswith("1 INFO   OctoBot Launcher")
        assert "Saving logs" in result

    def test_strips_real_shaped_warning_line(self):
        result = strip_log_line_timings(_SAMPLE_WARNING_LINE + "\n")
        assert result.startswith("1 WARNING Configuration")

    def test_numbers_consecutive_info_lines(self):
        body = _SAMPLE_INFO_LINE + "\n" + _SAMPLE_INFO_LINE + "\n"
        result = strip_log_line_timings(body)
        lines = result.splitlines()
        assert lines[0].startswith("1 INFO")
        assert lines[1].startswith("2 INFO")

    def test_strips_error_and_debug_levels(self):
        error_line = "2026-01-01 00:00:00 ERROR  MyModule             app.py:1           failed\n"
        debug_line = "2026-01-01 00:00:01 DEBUG  MyModule             app.py:2           trace\n"
        result = strip_log_line_timings(error_line + debug_line)
        lines = result.splitlines()
        assert lines[0].startswith("1 ERROR")
        assert lines[1].startswith("2 DEBUG")

    def test_leaves_blank_and_traceback_lines_unchanged(self):
        body = "\n  File \"foo.py\", line 1\n"
        assert strip_log_line_timings(body) == body

    def test_rejects_non_timing_prefix_before_level(self):
        line = "Note INFO about something\n"
        assert strip_log_line_timings(line) == line


class TestBuildLogsZipRemoveTiming:
    def test_remove_timing_transforms_zip_content(self, tmp_path):
        (tmp_path / "task-a.log").write_text(_SAMPLE_INFO_LINE + "\n")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a"], remove_timing=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            content = zip_file.read("task-a.log").decode()
            assert content.startswith("1 INFO   OctoBot Launcher")

    def test_each_file_starts_sequence_at_one(self, tmp_path):
        (tmp_path / "task-a.log").write_text(_SAMPLE_INFO_LINE + "\n")
        (tmp_path / "task-b.log").write_text(_SAMPLE_WARNING_LINE + "\n")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a", "task-b"], remove_timing=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.read("task-a.log").decode().startswith("1 INFO")
            assert zip_file.read("task-b.log").decode().startswith("1 WARNING")

    def test_remove_timing_false_matches_raw_file(self, tmp_path):
        raw = _SAMPLE_INFO_LINE + "\n"
        (tmp_path / "task-a.log").write_bytes(raw.encode())
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a"], remove_timing=False)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.read("task-a.log") == raw.encode()


class TestBuildLogsZip:
    def test_returns_none_when_no_files(self, tmp_path):
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            assert build_logs_zip(["missing-id"]) is None

    def test_zips_existing_log_files_and_skips_missing(self, tmp_path):
        (tmp_path / "task-a.log").write_text("hello a")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a", "task-missing"])
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.namelist() == ["task-a.log"]
            assert zip_file.read("task-a.log") == b"hello a"

    def test_latest_only_zips_flat_log(self, tmp_path):
        (tmp_path / "task-a.log").write_text("hello a")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a"], latest_only=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.namelist() == ["task-a.log"]

    def test_latest_only_picks_active_log_in_folder(self, tmp_path):
        task_dir = tmp_path / "task-a"
        task_dir.mkdir()
        (task_dir / "OctoBot.log").write_text("current")
        (task_dir / "OctoBot.log.1").write_text("backup")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a"], latest_only=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.namelist() == ["task-a/OctoBot.log"]
            assert zip_file.read("task-a/OctoBot.log") == b"current"

    def test_latest_only_includes_flat_and_folder(self, tmp_path):
        (tmp_path / "task-a.log").write_text("flat")
        task_dir = tmp_path / "task-a"
        task_dir.mkdir()
        (task_dir / "OctoBot.log").write_text("process")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a"], latest_only=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert sorted(zip_file.namelist()) == ["task-a.log", "task-a/OctoBot.log"]

    def test_latest_only_skips_missing_tasks(self, tmp_path):
        (tmp_path / "task-a.log").write_text("hello a")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            archive = build_logs_zip(["task-a", "task-missing"], latest_only=True)
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.namelist() == ["task-a.log"]


class TestBuildMainLogsZip:
    def test_returns_none_when_folder_missing(self, tmp_path):
        missing_folder = tmp_path / "missing"
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(missing_folder)):
            assert build_main_logs_zip() is None

    def test_zips_top_level_log_files_and_ignores_subfolders(self, tmp_path):
        (tmp_path / "OctoBot.log").write_text("main log")
        (tmp_path / "automations").mkdir()
        (tmp_path / "automations" / "task-a.log").write_text("automation log")
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            archive = build_main_logs_zip()
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert zip_file.namelist() == ["OctoBot.log"]
            assert zip_file.read("OctoBot.log") == b"main log"

    def test_zips_rotated_log_backups(self, tmp_path):
        (tmp_path / "OctoBot.log").write_text("current")
        (tmp_path / "OctoBot.log.1").write_text("backup 1")
        (tmp_path / "OctoBot.log.2").write_text("backup 2")
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            archive = build_main_logs_zip()
        assert archive is not None
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            assert sorted(zip_file.namelist()) == [
                "OctoBot.log",
                "OctoBot.log.1",
                "OctoBot.log.2",
            ]


# POST /logs/export requires authentication, like every other data route
class TestExportLogsRequireAuth:
    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.post("/api/v1/logs/export", json={"task_ids": ["task-a"]})
        assert response.status_code == 401

    def test_wrong_passphrase_returns_401(self, client, mock_auth):
        response = client.post(
            "/api/v1/logs/export",
            json={"task_ids": ["task-a"]},
            headers=_auth_header(TENANT_ADDRESS, "wrong"),
        )
        _assert_auth_error_response(response, "auth_invalid_passphrase")

    def test_unknown_wallet_returns_401(self, client, mock_auth):
        response = client.post(
            "/api/v1/logs/export",
            json={"task_ids": ["task-a"]},
            headers=_auth_header("0xdeadbeef", ADMIN_PASSPHRASE),
        )
        _assert_auth_error_response(response, "auth_wallet_not_found")


class TestExportLogs:
    def test_empty_body_exports_main_logs(self, admin_client, tmp_path):
        (tmp_path / "OctoBot.log").write_text("main log line")
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post("/api/v1/logs/export", json={})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.namelist() == ["OctoBot.log"]

    def test_empty_body_exports_rotated_main_logs(self, admin_client, tmp_path):
        (tmp_path / "OctoBot.log").write_text("current")
        (tmp_path / "OctoBot.log.1").write_text("backup 1")
        (tmp_path / "OctoBot.log.2").write_text("backup 2")
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post("/api/v1/logs/export", json={})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert sorted(zip_file.namelist()) == [
                "OctoBot.log",
                "OctoBot.log.1",
                "OctoBot.log.2",
            ]

    def test_null_task_ids_exports_main_logs(self, admin_client, tmp_path):
        (tmp_path / "OctoBot.log").write_text("main log line")
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post("/api/v1/logs/export", json={"task_ids": None})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.namelist() == ["OctoBot.log"]

    def test_no_main_logs_returns_404(self, admin_client, tmp_path):
        with mock.patch.object(octobot_node.constants, "BASE_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post("/api/v1/logs/export", json={})
        assert response.status_code == 404
        assert response.json()["detail"] == "No logs found in the node logs folder"

    def test_invalid_task_id_returns_400(self, admin_client):
        response = admin_client.post(
            "/api/v1/logs/export", json={"task_ids": ["../etc/passwd"]}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid task id"

    def test_no_logs_returns_404(self, admin_client, tmp_path):
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post(
                "/api/v1/logs/export", json={"task_ids": ["task-a"]}
            )
        assert response.status_code == 404
        assert response.json()["detail"] == "No logs found for the selected OctoBots"

    def test_returns_zip_with_selected_logs(self, admin_client, tmp_path):
        (tmp_path / "task-a.log").write_text("log line a")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post(
                "/api/v1/logs/export", json={"task_ids": ["task-a"]}
            )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.namelist() == ["task-a.log"]
            assert zip_file.read("task-a.log") == b"log line a"

    def test_export_latest_only_route(self, admin_client, tmp_path):
        task_dir = tmp_path / "task-a"
        task_dir.mkdir()
        (task_dir / "OctoBot.log").write_text("process log")
        (task_dir / "OctoBot.log.1").write_text("rotated")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post(
                "/api/v1/logs/export",
                json={"task_ids": ["task-a"], "latest_only": True},
            )
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.namelist() == ["task-a/OctoBot.log"]
            assert zip_file.read("task-a/OctoBot.log") == b"process log"

    def test_export_remove_timing_route(self, admin_client, tmp_path):
        (tmp_path / "task-a.log").write_text(_SAMPLE_INFO_LINE + "\n")
        with mock.patch.object(octobot_node.constants, "AUTOMATION_LOGS_FOLDER", str(tmp_path)):
            response = admin_client.post(
                "/api/v1/logs/export",
                json={"task_ids": ["task-a"], "remove_timing": True},
            )
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.read("task-a.log").decode().startswith("1 INFO")
