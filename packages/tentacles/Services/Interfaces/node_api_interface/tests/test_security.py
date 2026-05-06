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
import uuid
from unittest.mock import AsyncMock, patch

from .conftest import (
    ADMIN_ADDRESS,
    ADMIN_PASSPHRASE,
    TENANT_ADDRESS,
    TENANT_PASSPHRASE,
)


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _admin_header() -> dict:
    return _auth_header(ADMIN_ADDRESS, ADMIN_PASSPHRASE)


# /logs/share path traversal prevention
class TestLogsPathTraversal:
    def test_dotdot_automation_id_rejected(self, admin_client, mock_auth):
        resp = admin_client.post("/api/v1/logs/share", json={"automation_ids": ["../../etc/passwd"]})
        assert resp.status_code == 400

    def test_slash_in_automation_id_rejected(self, admin_client, mock_auth):
        resp = admin_client.post("/api/v1/logs/share", json={"automation_ids": ["some/path"]})
        assert resp.status_code == 400

    def test_dot_in_automation_id_rejected(self, admin_client, mock_auth):
        resp = admin_client.post("/api/v1/logs/share", json={"automation_ids": ["../sibling"]})
        assert resp.status_code == 400

    def test_valid_alphanumeric_id_accepted(self, admin_client, mock_auth):
        with patch(
            "octobot.community.errors_upload.error_sharing.share_logs",
            new=AsyncMock(return_value={"errorId": "x", "errorSecret": "y"}),
        ):
            resp = admin_client.post("/api/v1/logs/share", json={"automation_ids": ["auto-123_abc"]})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_no_ids_accepted(self, admin_client, mock_auth):
        with patch(
            "octobot.community.errors_upload.error_sharing.share_logs",
            new=AsyncMock(return_value={"errorId": "x", "errorSecret": "y"}),
        ):
            resp = admin_client.post("/api/v1/logs/share", json={})
        assert resp.status_code == 200


# /logs/share temp file must be cleaned up regardless of outcome
class TestLogsTempFileCleanup:
    def test_temp_file_deleted_on_success(self, admin_client, mock_auth, tmp_path):
        import os
        import tempfile

        created: list[str] = []
        real_ntf = tempfile.NamedTemporaryFile

        def capturing_ntf(**kwargs):
            f = real_ntf(**kwargs)
            created.append(f.name)
            return f

        with patch("tempfile.NamedTemporaryFile", side_effect=capturing_ntf), \
             patch(
                "octobot.community.errors_upload.error_sharing.share_logs",
                new=AsyncMock(return_value={"errorId": "x", "errorSecret": "y"}),
             ):
            resp = admin_client.post("/api/v1/logs/share", json={})

        assert resp.status_code == 200
        for path in created:
            assert not os.path.exists(path), f"Temp file {path} was not deleted"

    def test_temp_file_deleted_on_exception(self, admin_client, mock_auth):
        import os
        import tempfile

        created: list[str] = []
        real_ntf = tempfile.NamedTemporaryFile

        def capturing_ntf(**kwargs):
            f = real_ntf(**kwargs)
            created.append(f.name)
            return f

        with patch("tempfile.NamedTemporaryFile", side_effect=capturing_ntf), \
             patch(
                "octobot.community.errors_upload.error_sharing.share_logs",
                new=AsyncMock(side_effect=RuntimeError("network failure")),
             ):
            resp = admin_client.post("/api/v1/logs/share", json={})

        assert resp.status_code == 200  # generic error, not 500
        for path in created:
            assert not os.path.exists(path), f"Temp file {path} was not deleted after exception"


# /logs/share must not leak internal exception details to callers
class TestLogsErrorDisclosure:
    def test_internal_path_not_in_response(self, admin_client, mock_auth):
        secret = "/var/lib/octobot/private/db.sqlite"
        with patch(
            "octobot.community.errors_upload.error_sharing.share_logs",
            new=AsyncMock(side_effect=RuntimeError(f"cannot open {secret}")),
        ):
            resp = admin_client.post("/api/v1/logs/share", json={})

        body = resp.json()
        assert body["success"] is False
        assert secret not in str(body)
        assert body["error"] == "Failed to share logs"


# /nodes endpoints require authentication
class TestNodeEndpointsRequireAuth:
    def test_nodes_me_without_auth_returns_401(self, client, mock_auth):
        resp = client.get("/api/v1/nodes/me")
        assert resp.status_code == 401

    def test_nodes_config_without_auth_returns_401(self, client, mock_auth):
        resp = client.get("/api/v1/nodes/config")
        assert resp.status_code == 401

    def test_nodes_patch_config_without_auth_returns_401(self, client, mock_auth):
        resp = client.patch("/api/v1/nodes/config", json={"node_type": "master"})
        assert resp.status_code == 401


# PATCH /nodes/config typed schema — rejects invalid values and coerces bools correctly
class TestNodeConfigSchema:
    def test_invalid_node_type_rejected(self, admin_client, mock_auth):
        resp = admin_client.patch("/api/v1/nodes/config", json={"node_type": "evil"})
        assert resp.status_code == 422

    def test_non_boolean_use_dedicated_log_rejected(self, admin_client, mock_auth):
        resp = admin_client.patch(
            "/api/v1/nodes/config",
            json={"use_dedicated_log_file_per_automation": "not-a-bool"},
        )
        assert resp.status_code == 422

    def test_valid_patch_succeeds(self, admin_client, mock_auth):
        with patch("octobot_node.config.settings") as s, \
             patch("octobot_node.scheduler.scheduler.Scheduler._setup_workflow_logging"):
            s.IS_MASTER_MODE = False
            s.USE_DEDICATED_LOG_FILE_PER_AUTOMATION = False
            s.tasks_encryption_enabled = False
            import octobot_node.constants
            with patch.object(octobot_node.constants, "TASKS_ENCRYPTION_ENV_VARS", []):
                resp = admin_client.patch(
                    "/api/v1/nodes/config",
                    json={"node_type": "standalone", "use_dedicated_log_file_per_automation": True},
                )
        assert resp.status_code == 200


# GET /tasks/ pagination limit must be capped to prevent DoS
class TestPaginationLimit:
    def test_huge_limit_does_not_crash(self, admin_client, mock_auth):
        import octobot_node.models
        tasks = [octobot_node.models.Task(id=str(uuid.uuid4())) for _ in range(10)]
        with patch(
            "octobot_node.scheduler.api.get_all_tasks",
            new=AsyncMock(return_value=tasks),
        ):
            resp = admin_client.get("/api/v1/tasks/?limit=99999999&page=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_negative_limit_normalised(self, admin_client, mock_auth):
        with patch(
            "octobot_node.scheduler.api.get_all_tasks",
            new=AsyncMock(return_value=[]),
        ):
            resp = admin_client.get("/api/v1/tasks/?limit=-50")
        assert resp.status_code == 200


# GET /tasks/server-public-keys requires authentication
class TestServerPublicKeysAuth:
    def test_server_public_keys_without_auth_returns_401(self, client, mock_auth):
        resp = client.get("/api/v1/tasks/server-public-keys")
        assert resp.status_code == 401


# DELETE /tasks/ must not expose internal ValueError details
class TestDeleteTaskErrorDisclosure:
    def test_delete_missing_task_returns_generic_message(self, admin_client, mock_auth):
        internal = "workflow_id=abc not found in internal dbos table"
        task_id = str(uuid.uuid4())
        with patch(
            "octobot_node.scheduler.api.delete_tasks",
            new=AsyncMock(side_effect=ValueError(internal)),
        ):
            resp = admin_client.delete(f"/api/v1/tasks/?taskIds={task_id}")
        assert resp.status_code == 404
        body = resp.json()
        assert internal not in str(body)
        assert body.get("detail") == "Task not found"


# All 401 responses must carry WWW-Authenticate: Basic
class TestWWWAuthenticateHeader:
    def test_missing_credentials_returns_www_authenticate(self, client, mock_auth):
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate", "").lower().startswith("basic")

    def test_wrong_passphrase_returns_www_authenticate(self, client, mock_auth):
        bad_header = _auth_header(ADMIN_ADDRESS, "wrongpassword")
        resp = client.get("/api/v1/tasks/", headers=bad_header)
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate", "").lower().startswith("basic")

    def test_unknown_wallet_returns_www_authenticate(self, client, mock_auth):
        bad_header = _auth_header("0xdeadbeef", ADMIN_PASSPHRASE)
        resp = client.get("/api/v1/tasks/", headers=bad_header)
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate", "").lower().startswith("basic")
