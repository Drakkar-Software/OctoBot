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
import time
from unittest import mock

import pytest
from aiohttp.test_utils import TestServer
from fastapi.testclient import TestClient

import tentacles.Services.Interfaces.node_api_interface.api.node_setup_gate as node_setup_gate
import tentacles.Services.Interfaces.node_api_interface as node_api_interface_module
import tentacles.Services.Interfaces.node_api_interface.mobile_ui as mobile_ui

from .mobile_ui import mobile_ui_test_server as test_server


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


class TestMobileUiFirstRunRoutes:
    @pytest.fixture()
    def unconfigured_auth(self):
        auth = mock.MagicMock()
        auth.is_node_wallet_configured.return_value = False
        auth.list_wallets.return_value = []
        with mock.patch(
            "octobot.community.authentication.CommunityAuthentication.instance",
            return_value=auth,
        ):
            yield auth

    def test_first_run_status_without_auth_unconfigured_node(
        self, client, configured_store, unconfigured_auth
    ):
        _private_key, store = configured_store
        client.app.state.mobile_ui_store = store
        response = client.get("/api/v1/mobile-ui/first-run/status")
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "not_installed"

    def test_first_run_install_without_auth_unconfigured_node(
        self, client, unconfigured_auth, configured_store
    ):
        _private_key, store = configured_store
        client.app.state.mobile_ui_store = store
        response = client.post("/api/v1/mobile-ui/first-run/install")
        assert response.status_code == 202, response.text

    def test_first_run_endpoints_reject_configured_node(
        self, client, mock_auth, configured_store
    ):
        _private_key, store = configured_store
        client.app.state.mobile_ui_store = store
        assert store._install_task is None
        status_resp = client.get("/api/v1/mobile-ui/first-run/status")
        assert status_resp.status_code == 409, status_resp.text
        assert status_resp.json()["detail"] == node_setup_gate.NODE_ALREADY_CONFIGURED_DETAIL
        install_resp = client.post("/api/v1/mobile-ui/first-run/install")
        assert install_resp.status_code == 409, install_resp.text
        assert install_resp.json()["detail"] == node_setup_gate.NODE_ALREADY_CONFIGURED_DETAIL
        assert store._install_task is None
        assert store.get_status()["state"] == "not_installed"

    def test_first_run_install_trust_missing_returns_not_configured(
        self, client, unconfigured_auth, tmp_path
    ):
        store = mobile_ui.MobileUiStore(tmp_path, "", "")
        client.app.state.mobile_ui_store = store
        response = client.post("/api/v1/mobile-ui/first-run/install")
        assert response.status_code == 202, response.text
        assert response.json()["state"] == "not_configured"
        assert store._install_task is None
        status_resp = client.get("/api/v1/mobile-ui/first-run/status")
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["state"] == "not_configured"

    def test_first_run_concurrent_install_single_task(
        self, client, unconfigured_auth, configured_store
    ):
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
                client.app.state.mobile_ui_store = store
                first = client.post("/api/v1/mobile-ui/first-run/install")
                second = client.post("/api/v1/mobile-ui/first-run/install")
                assert first.status_code == 202
                assert second.status_code == 202
                assert first.json()["state"] == "installing"
                assert second.json()["state"] == "installing"

        asyncio.run(_run())

    def test_first_run_mid_download_wallet_registered(
        self, unit_app, admin_client, configured_store, mock_auth
    ):
        private_key, store = configured_store
        wallets_before = list(mock_auth.list_wallets.return_value)
        mobile_ui.add_mobile_ui_routes(unit_app)
        version = "abcd1234abcd1234"
        index = b"<html>mobile</html>"
        js = b"js"
        logo = b"png"
        files = [
            test_server.file_entry("index.html", index),
            test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
            test_server.file_entry("assets/logo.png", logo),
        ]
        state = test_server.MobileUiTestServerState()
        state.manifest_delay_seconds = 0.4
        state.file_contents = {
            (version, "index.html"): index,
            (version, "_expo/static/js/web/entry-abc.js"): js,
            (version, "assets/logo.png"): logo,
        }
        state.manifest = test_server.sign_manifest(private_key, version, files)

        async def _run():
            async with TestServer(test_server.build_application(state)) as server:
                store.update_base_url = str(server.make_url("")).rstrip("/")
                unit_app.state.mobile_ui_store = store
                unconfigured = mock.MagicMock()
                unconfigured.is_node_wallet_configured.return_value = False
                unconfigured.list_wallets.return_value = []
                with TestClient(unit_app, raise_server_exceptions=False) as bare_client:
                    with mock.patch(
                        "octobot.community.authentication.CommunityAuthentication.instance",
                        return_value=unconfigured,
                    ):
                        start_resp = bare_client.post("/api/v1/mobile-ui/first-run/install")
                        assert start_resp.status_code == 202, start_resp.text
                    await asyncio.sleep(0.05)
                    with mock.patch(
                        "octobot.community.authentication.CommunityAuthentication.instance",
                        return_value=mock_auth,
                    ):
                        blocked = bare_client.get("/api/v1/mobile-ui/first-run/status")
                        assert blocked.status_code == 409
                        assert (
                            blocked.json()["detail"]
                            == node_setup_gate.NODE_ALREADY_CONFIGURED_DETAIL
                        )
                        blocked_install = bare_client.post(
                            "/api/v1/mobile-ui/first-run/install"
                        )
                        assert blocked_install.status_code == 409
                        assert (
                            blocked_install.json()["detail"]
                            == node_setup_gate.NODE_ALREADY_CONFIGURED_DETAIL
                        )
                    deadline = time.time() + 15
                    while time.time() < deadline:
                        admin_status = admin_client.get("/api/v1/mobile-ui/status")
                        if admin_status.json()["state"] == "ready":
                            break
                        await asyncio.sleep(0.05)
                    else:
                        raise AssertionError(
                            "install did not reach ready after wallet registration"
                        )
                    mobile_page = bare_client.get("/mobile/")
                    assert mobile_page.status_code == 200, mobile_page.text
                    assert "<html>mobile</html>" in mobile_page.text
                    assert list(mock_auth.list_wallets.return_value) == wallets_before

        asyncio.run(_run())
