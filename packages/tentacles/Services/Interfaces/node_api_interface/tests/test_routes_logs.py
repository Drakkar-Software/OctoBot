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
    from tentacles.Services.Interfaces.node_api_interface.api.routes.logs import build_logs_zip
except ImportError:
    from api.routes.logs import build_logs_zip  # type: ignore[no-redef]

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE, TENANT_ADDRESS


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _assert_invalid_auth_response(response) -> None:
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect address or passphrase"}


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
        _assert_invalid_auth_response(response)

    def test_unknown_wallet_returns_401(self, client, mock_auth):
        response = client.post(
            "/api/v1/logs/export",
            json={"task_ids": ["task-a"]},
            headers=_auth_header("0xdeadbeef", ADMIN_PASSPHRASE),
        )
        _assert_invalid_auth_response(response)

    def test_missing_credentials_returns_www_authenticate(self, client, mock_auth):
        response = client.post("/api/v1/logs/export", json={"task_ids": ["task-a"]})
        assert response.status_code == 401
        assert response.headers.get("www-authenticate", "").lower().startswith("basic")


class TestExportLogs:
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
