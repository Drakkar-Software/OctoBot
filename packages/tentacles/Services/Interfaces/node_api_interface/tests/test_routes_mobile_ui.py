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

import asyncio
import os
import sys
import time

import pytest
from aiohttp.test_utils import TestServer

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_MOBILE_UI_TESTS = os.path.join(_TESTS_DIR, "mobile_ui")
if _MOBILE_UI_TESTS not in sys.path:
    sys.path.insert(0, _MOBILE_UI_TESTS)

import mobile_ui_test_server as test_server
import tentacles.Services.Interfaces.node_api_interface as node_api_interface_module
import tentacles.Services.Interfaces.node_api_interface.mobile_ui as mobile_ui


@pytest.fixture()
def configured_store(tmp_path):
    private_key, public_key_b64 = test_server.generate_keypair()
    store = mobile_ui.MobileUiStore(tmp_path, "http://placeholder", public_key_b64)
    return private_key, store


@pytest.fixture()
def mobile_ui_unit_app(unit_app, configured_store):
    _private_key, store = configured_store
    unit_app.state.mobile_ui_store = store
    mobile_ui.add_mobile_ui_routes(unit_app)
    return unit_app


class TestMobileUiRoutesAuth:
    def test_status_without_auth_returns_401(self, client, mock_auth):
        response = client.get("/api/v1/mobile-ui/status")
        assert response.status_code == 401, response.text

    def test_install_without_auth_returns_401(self, client, mock_auth):
        response = client.post("/api/v1/mobile-ui/install")
        assert response.status_code == 401, response.text

    def test_tenant_can_get_status(self, tenant_client, mobile_ui_unit_app):
        response = tenant_client.get("/api/v1/mobile-ui/status")
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "not_installed"

    def test_tenant_install_forbidden(self, tenant_client, mobile_ui_unit_app):
        response = tenant_client.post("/api/v1/mobile-ui/install")
        assert response.status_code == 403, response.text

    def test_check_without_auth_returns_401(self, client, mock_auth):
        response = client.post("/api/v1/mobile-ui/check")
        assert response.status_code == 401, response.text

    def test_tenant_check_forbidden(self, tenant_client, mobile_ui_unit_app):
        response = tenant_client.post("/api/v1/mobile-ui/check")
        assert response.status_code == 403, response.text


class TestMobileUiRoutesInstall:
    def test_admin_install_eventually_ready(self, admin_client, configured_store):
        private_key, store = configured_store
        version = "abcd1234abcd1234"
        index = b"<html></html>"
        js = b"js"
        logo = b"png"
        files = [
            test_server.file_entry("index.html", index),
            test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
            test_server.file_entry("assets/logo.png", logo),
        ]
        state = test_server.MobileUiTestServerState()
        state.manifest = test_server.sign_manifest(private_key, version, files)
        state.file_contents = {
            (version, "index.html"): index,
            (version, "_expo/static/js/web/entry-abc.js"): js,
            (version, "assets/logo.png"): logo,
        }

        async def _run():
            async with TestServer(test_server.build_application(state)) as server:
                store.update_base_url = str(server.make_url("")).rstrip("/")
                admin_client.app.state.mobile_ui_store = store
                response = admin_client.post("/api/v1/mobile-ui/install")
                assert response.status_code == 202, response.text
                deadline = time.time() + 10
                while time.time() < deadline:
                    status = admin_client.get("/api/v1/mobile-ui/status").json()
                    if status["state"] == "ready":
                        return
                    await asyncio.sleep(0.05)
                raise AssertionError("install did not reach ready state")

        asyncio.run(_run())





class TestMobileUiRoutesCheck:
    def test_admin_check_newer_manifest(self, admin_client, configured_store):
        private_key, store = configured_store
        version1 = "abcd1234abcd1234"
        version2 = "beefbeefbeefbeef"
        index = b"<html></html>"
        js = b"js"
        logo = b"png"
        files = [
            test_server.file_entry("index.html", index),
            test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
            test_server.file_entry("assets/logo.png", logo),
        ]
        state = test_server.MobileUiTestServerState()
        state.file_contents = {
            (version1, "index.html"): index,
            (version1, "_expo/static/js/web/entry-abc.js"): js,
            (version1, "assets/logo.png"): logo,
            (version2, "index.html"): index,
            (version2, "_expo/static/js/web/entry-abc.js"): js,
            (version2, "assets/logo.png"): logo,
        }

        async def _run():
            async with TestServer(test_server.build_application(state)) as server:
                store.update_base_url = str(server.make_url("")).rstrip("/")
                admin_client.app.state.mobile_ui_store = store
                state.manifest = test_server.sign_manifest(
                    private_key, version1, files, sequence=100
                )
                install_resp = admin_client.post("/api/v1/mobile-ui/install")
                assert install_resp.status_code == 202, install_resp.text
                deadline = time.time() + 10
                while time.time() < deadline:
                    if admin_client.get("/api/v1/mobile-ui/status").json()["state"] == "ready":
                        break
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("install did not reach ready state")
                state.manifest = test_server.sign_manifest(
                    private_key, version2, files, sequence=200
                )
                state.reset_requests()
                response = await asyncio.to_thread(
                    admin_client.post, "/api/v1/mobile-ui/check"
                )
                assert response.status_code == 200, response.text
                body = response.json()
                assert body["update_available"] is True
                assert body["latest_version"] == version2
                assert body["installed_version"] == version1
                assert state.file_requests == []

        asyncio.run(_run())

    def test_admin_check_unconfigured(self, admin_client, unit_app, tmp_path):
        unit_app.state.mobile_ui_store = mobile_ui.MobileUiStore(tmp_path, "", "")
        response = admin_client.post("/api/v1/mobile-ui/check")
        assert response.status_code == 200
        assert response.json()["state"] == "not_configured"

    def test_admin_check_rollback(self, admin_client, configured_store):
        private_key, store = configured_store
        version1 = "cccccccccccccccc"
        version2 = "dddddddddddddddd"
        index = b"<html></html>"
        js = b"js"
        logo = b"png"
        files = [
            test_server.file_entry("index.html", index),
            test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
            test_server.file_entry("assets/logo.png", logo),
        ]
        state = test_server.MobileUiTestServerState()
        state.file_contents = {
            (version1, "index.html"): index,
            (version1, "_expo/static/js/web/entry-abc.js"): js,
            (version1, "assets/logo.png"): logo,
            (version2, "index.html"): index,
            (version2, "_expo/static/js/web/entry-abc.js"): js,
            (version2, "assets/logo.png"): logo,
        }

        async def _run():
            async with TestServer(test_server.build_application(state)) as server:
                store.update_base_url = str(server.make_url("")).rstrip("/")
                admin_client.app.state.mobile_ui_store = store
                state.manifest = test_server.sign_manifest(
                    private_key, version1, files, sequence=300
                )
                install_resp = admin_client.post("/api/v1/mobile-ui/install")
                assert install_resp.status_code == 202, install_resp.text
                deadline = time.time() + 10
                while time.time() < deadline:
                    if admin_client.get("/api/v1/mobile-ui/status").json()["state"] == "ready":
                        break
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("install did not reach ready state")
                state.manifest = test_server.sign_manifest(
                    private_key, version2, files, sequence=50
                )
                response = await asyncio.to_thread(
                    admin_client.post, "/api/v1/mobile-ui/check"
                )
                assert response.status_code == 200, response.text
                assert response.json()["last_error"] == "rollback_rejected"

        asyncio.run(_run())


class TestMobileUiUnconfigured:
    def test_unconfigured_status(self, admin_client, unit_app, tmp_path):
        unit_app.state.mobile_ui_store = mobile_ui.MobileUiStore(tmp_path, "", "")
        response = admin_client.get("/api/v1/mobile-ui/status")
        assert response.status_code == 200
        assert response.json()["state"] == "not_configured"

    def test_unconfigured_install_returns_not_configured(self, admin_client, unit_app, tmp_path):
        unit_app.state.mobile_ui_store = mobile_ui.MobileUiStore(tmp_path, "", "")
        response = admin_client.post("/api/v1/mobile-ui/install")
        assert response.status_code == 202
        assert response.json()["state"] == "not_configured"


class TestCreateAppMobileRoutes:
    def test_create_app_registers_mobile_routes(self, app):
        paths = {getattr(route, "path", None) for route in app.routes}
        assert "/mobile" in paths
        assert any(getattr(route, "path", None) == "/mobile/{path:path}" for route in app.routes)
        assert hasattr(app.state, "mobile_ui_store")
