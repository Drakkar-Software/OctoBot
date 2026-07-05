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

import octobot_services.constants as services_constants
import tentacles.Services.Interfaces.web_interface.models.distributions.node.configuration as node_configuration_model


class TestGetNodeLocalEndpoint:
    def test_uses_explicit_bind_address_when_not_loopback_or_any(self):
        node_api_service = mock.Mock()
        node_api_service.get_bind_port.return_value = 8000

        with mock.patch.object(
            node_configuration_model.Service_bases.NodeApiService,
            "instance",
            mock.Mock(return_value=node_api_service),
        ), mock.patch.dict("os.environ", {services_constants.ENV_NODE_API_ADDRESS: "192.168.1.42"}, clear=False):
            local_ip, port = node_configuration_model.get_node_local_endpoint()

        assert local_ip == "192.168.1.42"
        assert port == 8000

    def test_resolves_hostname_when_bind_address_is_any(self):
        node_api_service = mock.Mock()
        node_api_service.get_bind_port.return_value = 9001

        with mock.patch.object(
            node_configuration_model.Service_bases.NodeApiService,
            "instance",
            mock.Mock(return_value=node_api_service),
        ), mock.patch.dict("os.environ", {services_constants.ENV_NODE_API_ADDRESS: "0.0.0.0"}, clear=False), mock.patch.object(
            node_configuration_model.socket,
            "gethostbyname",
            mock.Mock(return_value="10.0.0.5"),
        ):
            local_ip, port = node_configuration_model.get_node_local_endpoint()

        assert local_ip == "10.0.0.5"
        assert port == 9001

    def test_falls_back_to_loopback_when_hostname_resolution_fails(self):
        node_api_service = mock.Mock()
        node_api_service.get_bind_port.return_value = 8000

        with mock.patch.object(
            node_configuration_model.Service_bases.NodeApiService,
            "instance",
            mock.Mock(return_value=node_api_service),
        ), mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            node_configuration_model.socket,
            "gethostbyname",
            mock.Mock(side_effect=OSError("hostname resolution failed")),
        ):
            local_ip, port = node_configuration_model.get_node_local_endpoint()

        assert local_ip == "127.0.0.1"
        assert port == 8000
