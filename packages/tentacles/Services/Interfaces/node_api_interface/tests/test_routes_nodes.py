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
import threading
import time

import mock

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE, TENANT_ADDRESS, TENANT_PASSPHRASE


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class TestStopNodeRequireAuth:
    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.post("/api/v1/nodes/stop")
        assert response.status_code == 401


class TestStopNodePrivileges:
    def test_tenant_returns_403(self, tenant_client):
        response = tenant_client.post("/api/v1/nodes/stop")
        assert response.status_code == 403
        assert response.json()["detail"] == "The user doesn't have enough privileges"

    def test_admin_returns_204_and_schedules_stop_bot(self, admin_client):
        stop_called = threading.Event()
        bot_api = mock.Mock()
        bot_api.stop_bot.side_effect = lambda: stop_called.set()

        with mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.api.routes.nodes.interfaces_util.get_bot_api",
            return_value=bot_api,
        ):
            response = admin_client.post("/api/v1/nodes/stop")
            assert response.status_code == 204
            assert not stop_called.is_set()
            assert stop_called.wait(timeout=2.0)
        bot_api.stop_bot.assert_called_once()

    def test_admin_with_basic_auth_returns_204(self, client, mock_auth):
        stop_called = threading.Event()
        bot_api = mock.Mock()
        bot_api.stop_bot.side_effect = lambda: stop_called.set()

        with mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.api.routes.nodes.interfaces_util.get_bot_api",
            return_value=bot_api,
        ):
            response = client.post(
                "/api/v1/nodes/stop",
                headers=_auth_header(ADMIN_ADDRESS, ADMIN_PASSPHRASE),
            )
            assert response.status_code == 204
            assert stop_called.wait(timeout=2.0)
        bot_api.stop_bot.assert_called_once()

    def test_tenant_with_basic_auth_returns_403(self, client, mock_auth):
        response = client.post(
            "/api/v1/nodes/stop",
            headers=_auth_header(TENANT_ADDRESS, TENANT_PASSPHRASE),
        )
        assert response.status_code == 403
