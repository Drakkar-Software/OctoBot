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

import mock

try:
    import tentacles.Services.Interfaces.node_api_interface.core.network as network
except ImportError:
    from core import network


NETWORK_MODULE = "tentacles.Services.Interfaces.node_api_interface.core.network"


class TestGetVpnNetworkIp:
    def test_get_vpn_network_ip_delegates_with_tailscale_substring(self):
        with mock.patch(
            f"{NETWORK_MODULE}.commons_network.get_interface_ipv4_by_name_substring",
            return_value="100.64.0.1",
        ) as get_interface_ipv4:
            assert network.get_vpn_network_ip() == "100.64.0.1"
        get_interface_ipv4.assert_called_once_with(network.TAILSCALE_INTERFACE_NAME_SUBSTRING)


class TestGetLocalNetworkIp:
    def test_get_local_network_ip_delegates_to_commons(self):
        with mock.patch(
            f"{NETWORK_MODULE}.commons_network.get_local_network_ip",
            return_value="192.168.0.10",
        ) as get_local_network_ip:
            assert network.get_local_network_ip() == "192.168.0.10"
        get_local_network_ip.assert_called_once_with()
