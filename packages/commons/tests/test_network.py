#  Drakkar-Software OctoBot-Commons
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

import ipaddress
import socket

import mock
import psutil
import pytest

import octobot_commons.network as network


NETWORK_MODULE = "octobot_commons.network"


def _first_interface_ipv4():
    for interface_name, addresses in psutil.net_if_addrs().items():
        for address in addresses:
            if address.family == socket.AF_INET:
                return interface_name, address.address
    return None, None


class TestGetInterfaceIpv4ByNameSubstring:
    def test_returns_ipv4_when_interface_name_contains_substring(self):
        tailscale_address = mock.Mock()
        tailscale_address.family = socket.AF_INET
        tailscale_address.address = "100.64.0.1"
        with mock.patch(
            f"{NETWORK_MODULE}.psutil.net_if_addrs",
            return_value={"tailscale0": [tailscale_address]},
        ):
            assert network.get_interface_ipv4_by_name_substring("tailscale") == "100.64.0.1"

    def test_returns_none_when_no_matching_interface(self):
        with mock.patch(f"{NETWORK_MODULE}.psutil.net_if_addrs", return_value={}):
            assert network.get_interface_ipv4_by_name_substring("tailscale") is None

    def test_matches_substring_case_insensitively(self):
        tailscale_address = mock.Mock()
        tailscale_address.family = socket.AF_INET
        tailscale_address.address = "100.64.0.2"
        with mock.patch(
            f"{NETWORK_MODULE}.psutil.net_if_addrs",
            return_value={"Tailscale0": [tailscale_address]},
        ):
            assert network.get_interface_ipv4_by_name_substring("tailscale") == "100.64.0.2"

    def test_skips_interfaces_without_substring(self):
        ethernet_address = mock.Mock()
        ethernet_address.family = socket.AF_INET
        ethernet_address.address = "192.168.0.5"
        tailscale_address = mock.Mock()
        tailscale_address.family = socket.AF_INET
        tailscale_address.address = "100.64.0.3"
        with mock.patch(
            f"{NETWORK_MODULE}.psutil.net_if_addrs",
            return_value={
                "eth0": [ethernet_address],
                "tailscale0": [tailscale_address],
            },
        ):
            assert network.get_interface_ipv4_by_name_substring("tailscale") == "100.64.0.3"

    def test_skips_non_af_inet_addresses(self):
        ipv6_address = mock.Mock()
        ipv6_address.family = socket.AF_INET6
        ipv6_address.address = "fe80::1"
        with mock.patch(
            f"{NETWORK_MODULE}.psutil.net_if_addrs",
            return_value={"tailscale0": [ipv6_address]},
        ):
            assert network.get_interface_ipv4_by_name_substring("tailscale") is None

    def test_returns_first_af_inet_on_matching_interface(self):
        first_address = mock.Mock()
        first_address.family = socket.AF_INET
        first_address.address = "100.64.0.4"
        second_address = mock.Mock()
        second_address.family = socket.AF_INET
        second_address.address = "100.64.0.5"
        with mock.patch(
            f"{NETWORK_MODULE}.psutil.net_if_addrs",
            return_value={"tailscale0": [first_address, second_address]},
        ):
            assert network.get_interface_ipv4_by_name_substring("tailscale") == "100.64.0.4"


class TestGetInterfaceIpv4ByNameSubstringPsutilIntegration:
    def test_psutil_net_if_addrs_runs_without_error(self):
        interface_addresses = psutil.net_if_addrs()
        assert isinstance(interface_addresses, dict)

    def test_returns_none_for_nonexistent_substring(self):
        assert network.get_interface_ipv4_by_name_substring("__octobot_no_such_iface__") is None

    def test_returns_valid_ipv4_for_real_interface(self):
        interface_name, expected_ipv4 = _first_interface_ipv4()
        if interface_name is None:
            pytest.skip("No AF_INET network interface on this host")
        result = network.get_interface_ipv4_by_name_substring(interface_name.lower())
        assert result == expected_ipv4
        assert ipaddress.ip_address(result).version == 4


class TestGetLocalNetworkIp:
    def test_returns_udp_route_private_ip(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.42", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            assert network.get_local_network_ip() == "192.168.1.42"

    def test_falls_back_to_hostname_private_ip(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("8.8.8.8", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                return_value=[(None, None, None, None, ("10.0.0.5", 0))],
            ):
                assert network.get_local_network_ip() == "10.0.0.5"

    def test_returns_none_when_no_private_ip_found(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("127.0.0.1", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                side_effect=OSError,
            ):
                assert network.get_local_network_ip() is None

    def test_prefers_192_address_over_udp_10_address(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("10.0.0.5", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                return_value=[(None, None, None, None, ("192.168.1.42", 0))],
            ):
                assert network.get_local_network_ip() == "192.168.1.42"

    def test_prefers_192_address_from_hostname_candidates(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("8.8.8.8", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                return_value=[
                    (None, None, None, None, ("10.0.0.5", 0)),
                    (None, None, None, None, ("192.168.0.10", 0)),
                ],
            ):
                assert network.get_local_network_ip() == "192.168.0.10"

    def test_uses_udp_probe_constants(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.42", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            network.get_local_network_ip()
        mock_socket.connect.assert_called_once_with(
            (network.UDP_ROUTE_PROBE_HOST, network.UDP_ROUTE_PROBE_PORT),
        )

    def test_ignores_udp_non_private_candidate(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("8.8.8.8", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                return_value=[(None, None, None, None, ("10.0.0.5", 0))],
            ):
                assert network.get_local_network_ip() == "10.0.0.5"

    def test_deduplicates_udp_and_hostname_candidates(self):
        mock_socket = mock.MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.42", 54321)
        mock_socket.__enter__.return_value = mock_socket
        with mock.patch(f"{NETWORK_MODULE}.socket.socket", return_value=mock_socket):
            with mock.patch(
                f"{NETWORK_MODULE}.socket.getaddrinfo",
                return_value=[(None, None, None, None, ("192.168.1.42", 0))],
            ):
                assert network.get_local_network_ip() == "192.168.1.42"
