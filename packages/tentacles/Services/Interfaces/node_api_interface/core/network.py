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

import octobot_commons.network as commons_network

TAILSCALE_INTERFACE_NAME_SUBSTRING = "tailscale"
TAILSCALE_IPV4_PREFIX = "100." # tailscale ip range is 100.x.x.x/16


def get_vpn_network_ip() -> str | None:
    interface_ipv4 = commons_network.get_interface_ipv4_by_name_substring(
        TAILSCALE_INTERFACE_NAME_SUBSTRING,
    )
    if interface_ipv4 is not None and interface_ipv4.startswith(TAILSCALE_IPV4_PREFIX):
        return interface_ipv4
    return commons_network.get_interface_ipv4_by_prefix(TAILSCALE_IPV4_PREFIX)


def get_local_network_ip() -> str | None:
    return commons_network.get_local_network_ip()
