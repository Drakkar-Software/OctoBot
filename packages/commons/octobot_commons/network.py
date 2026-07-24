#  Drakkar-Software OctoBot
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

import psutil

PREFERRED_LOCAL_IPV4_PREFIX = "192."
UDP_ROUTE_PROBE_HOST = "8.8.8.8"
UDP_ROUTE_PROBE_PORT = 80


def _is_private_ipv4(ip_address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    return parsed.version == 4 and parsed.is_private and not parsed.is_loopback and not parsed.is_link_local


def _is_preferred_local_ipv4(ip_address: str) -> bool:
    return _is_private_ipv4(ip_address) and ip_address.startswith(PREFERRED_LOCAL_IPV4_PREFIX)


def _pick_preferred_local_ipv4(candidates: list[str]) -> str | None:
    private_candidates = [
        candidate for candidate in candidates if _is_private_ipv4(candidate)
    ]
    if not private_candidates:
        return None
    for candidate in private_candidates:
        if _is_preferred_local_ipv4(candidate):
            return candidate
    return private_candidates[0]


def _udp_route_local_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.connect((UDP_ROUTE_PROBE_HOST, UDP_ROUTE_PROBE_PORT))
            candidate = udp_socket.getsockname()[0]
    except OSError:
        return None
    if _is_private_ipv4(candidate):
        return candidate
    return None


def _hostname_private_ipv4_candidates() -> list[str]:
    candidates: list[str] = []
    try:
        address_infos = socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET)
    except OSError:
        return candidates
    for address_info in address_infos:
        sockaddr = address_info[4]
        if not sockaddr:
            continue
        candidate = sockaddr[0]
        if _is_private_ipv4(candidate) and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _get_local_network_ipv4() -> str | None:
    candidates: list[str] = []
    udp_candidate = _udp_route_local_ipv4()
    if udp_candidate is not None:
        candidates.append(udp_candidate)
    for hostname_candidate in _hostname_private_ipv4_candidates():
        if hostname_candidate not in candidates:
            candidates.append(hostname_candidate)
    return _pick_preferred_local_ipv4(candidates)


def get_interface_ipv4_by_name_substring(interface_name_substring: str) -> str | None:
    """
    Return the first IPv4 address on a network interface whose name contains the given substring.
    Interface name matching is case-insensitive.
    :param interface_name_substring: substring to match against interface names
    :return: the IPv4 address string, or None if no matching interface or address is found
    """
    for interface_name, addresses in psutil.net_if_addrs().items():
        if interface_name_substring not in interface_name.lower():
            continue
        for address in addresses:
            if address.family == socket.AF_INET:
                return address.address
    return None


def get_local_network_ip() -> str | None:
    """
    Return the preferred private IPv4 address for local network access.
    Uses UDP route probing and hostname resolution; prefers 192.* addresses when multiple candidates exist.
    :return: the local network IPv4 address string, or None if none is found
    """
    return _get_local_network_ipv4()
