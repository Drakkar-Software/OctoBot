#  Drakkar-Software OctoBot-Tentacles
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

import mock
import pytest

import octobot_services.constants as services_constants
import octobot_services.errors as services_errors
import tentacles.Services.Services_bases.node_api_service.node_api as node_api_service_module


class TestNodeApiServiceExternalHost:
    def test_get_node_external_host_falls_back_to_config_value(self, monkeypatch):
        monkeypatch.delenv(services_constants.ENV_NODE_EXTERNAL_HOST, raising=False)
        service = node_api_service_module.NodeApiService()
        service.node_external_host = "node.example.com"
        assert service.get_node_external_host() == "node.example.com"

    def test_get_node_external_host_returns_none_by_default(self, monkeypatch):
        monkeypatch.delenv(services_constants.ENV_NODE_EXTERNAL_HOST, raising=False)
        service = node_api_service_module.NodeApiService()
        service.node_external_host = None
        assert service.get_node_external_host() is None

    def test_env_var_overrides_config_value(self, monkeypatch):
        monkeypatch.setenv(services_constants.ENV_NODE_EXTERNAL_HOST, "env-host.example.com")
        service = node_api_service_module.NodeApiService()
        service.node_external_host = "config-host.example.com"
        assert service.get_node_external_host() == "env-host.example.com"

    def test_set_node_external_host_persists_and_updates_getter(self, monkeypatch):
        monkeypatch.delenv(services_constants.ENV_NODE_EXTERNAL_HOST, raising=False)
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            service.set_node_external_host("new-host.example.com:8000")
        save_mock.assert_called_once_with(
            services_constants.CONFIG_NODE_API,
            {services_constants.NODE_EXTERNAL_HOST: "new-host.example.com:8000"},
            update=True,
        )
        assert service.get_node_external_host() == "new-host.example.com:8000"

    def test_set_node_external_host_empty_string_clears_value(self, monkeypatch):
        monkeypatch.delenv(services_constants.ENV_NODE_EXTERNAL_HOST, raising=False)
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            service.set_node_external_host("")
        save_mock.assert_called_once_with(
            services_constants.CONFIG_NODE_API,
            {services_constants.NODE_EXTERNAL_HOST: None},
            update=True,
        )
        assert service.get_node_external_host() is None

    def test_set_node_external_host_without_edited_config_raises(self, monkeypatch):
        # reproduces the reported crash: edited_config was never injected by ServiceFactory (eg because
        # the owning interface's initialize() failed). Now raises a typed error instead of AttributeError.
        monkeypatch.delenv(services_constants.ENV_NODE_EXTERNAL_HOST, raising=False)
        service = node_api_service_module.NodeApiService()
        assert service.edited_config is None
        with pytest.raises(services_errors.ServiceConfigurationError):
            service.set_node_external_host("new-host.example.com:8000")
