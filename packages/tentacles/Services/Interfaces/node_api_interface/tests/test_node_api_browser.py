#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import pathlib

import mock
import pytest

import octobot_services.constants as services_constants
import tentacles.Services.Interfaces.node_api_interface.node_api as node_api_module


class TestShouldOpenNodeUiInBrowser:
    def test_defaults_to_true_when_config_key_missing(self):
        interface = node_api_module.NodeApiInterface({})
        assert interface._should_open_node_ui_in_browser() is True

    def test_returns_false_when_config_disables_auto_open(self):
        interface = node_api_module.NodeApiInterface({
            services_constants.CONFIG_CATEGORY_SERVICES: {
                services_constants.CONFIG_NODE_API: {
                    services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: False,
                }
            }
        })
        assert interface._should_open_node_ui_in_browser() is False


class TestOpenNodeUiOnBrowser:
    def test_open_node_ui_on_browser_uses_app_path(self):
        interface = node_api_module.NodeApiInterface({})
        interface.logger = mock.Mock()
        interface.port = 8000
        with mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.web_util.open_in_background_browser"
        ) as open_browser_mock:
            interface._open_node_ui_on_browser()
        open_browser_mock.assert_called_once_with("http://127.0.0.1:8000/app")


@pytest.mark.asyncio
class TestNodeApiInterfaceAutoOpenOnStart:
    async def test_async_run_opens_browser_when_enabled_and_dist_exists(self):
        interface = node_api_module.NodeApiInterface({})
        interface.logger = mock.Mock()
        interface.node_api_service = mock.Mock()
        interface.node_api_service.get_bind_host.return_value = "0.0.0.0"
        interface.node_api_service.get_bind_port.return_value = 8000
        interface.node_api_service.get_node_sqlite_file.return_value = None
        interface.node_api_service.get_node_postgres_url.return_value = None
        interface.node_api_service.get_backend_cors_origins.return_value = ""
        interface.node_api_service.get_backend_cors_origin_regex.return_value = ""
        interface.server = mock.Mock()
        interface.server.serve = mock.AsyncMock()
        dist_path = pathlib.Path("/tmp/node-ui-dist")
        with mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.scheduler.is_initialized",
            return_value=True,
        ), mock.patch.object(
            interface,
            "create_app",
            return_value=mock.Mock(),
        ), mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.get_dist_directory",
            return_value=dist_path,
        ), mock.patch.object(
            interface,
            "_open_node_ui_on_browser",
            mock.Mock(),
        ) as open_browser_mock, mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.uvicorn.Config",
        ), mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.uvicorn.Server",
        ) as server_class_mock:
            server_class_mock.return_value = interface.server
            await interface._async_run()
        open_browser_mock.assert_called_once_with()

    async def test_async_run_skips_browser_when_auto_open_disabled(self):
        interface = node_api_module.NodeApiInterface({
            services_constants.CONFIG_CATEGORY_SERVICES: {
                services_constants.CONFIG_NODE_API: {
                    services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: False,
                }
            }
        })
        interface.logger = mock.Mock()
        interface.node_api_service = mock.Mock()
        interface.node_api_service.get_bind_host.return_value = "0.0.0.0"
        interface.node_api_service.get_bind_port.return_value = 8000
        interface.node_api_service.get_node_sqlite_file.return_value = None
        interface.node_api_service.get_node_postgres_url.return_value = None
        interface.node_api_service.get_backend_cors_origins.return_value = ""
        interface.node_api_service.get_backend_cors_origin_regex.return_value = ""
        interface.server = mock.Mock()
        interface.server.serve = mock.AsyncMock()
        with mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.scheduler.is_initialized",
            return_value=True,
        ), mock.patch.object(
            interface,
            "create_app",
            return_value=mock.Mock(),
        ), mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.get_dist_directory",
            return_value=pathlib.Path("/tmp/node-ui-dist"),
        ), mock.patch.object(
            interface,
            "_open_node_ui_on_browser",
            mock.Mock(),
        ) as open_browser_mock, mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.uvicorn.Config",
        ), mock.patch(
            "tentacles.Services.Interfaces.node_api_interface.node_api.uvicorn.Server",
        ) as server_class_mock:
            server_class_mock.return_value = interface.server
            await interface._async_run()
        open_browser_mock.assert_not_called()
