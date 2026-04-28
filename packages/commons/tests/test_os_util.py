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
import mock
import socket
import pytest

import octobot_commons.os_util as os_util


def test_get_cpu_and_ram_usage():
    cpu, percent_ram, used_ram, process_ram, virtual_ram, unique_ram = os_util.get_cpu_and_ram_usage(0.1)
    assert isinstance(cpu, float)
    assert percent_ram > 0
    assert used_ram > 0
    assert process_ram > 0
    assert virtual_ram > 0
    assert unique_ram > 0


class TestTcpPortIsFree:
    def test_returns_false_when_tcp_listener_holds_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            bound_port = listener.getsockname()[1]
            assert os_util.tcp_port_is_free("127.0.0.1", bound_port) is False

    def test_returns_true_after_listener_released(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            bound_port = listener.getsockname()[1]
        assert os_util.tcp_port_is_free("127.0.0.1", bound_port) is True


class TestFindFirstFreeListenPortAfterBase:
    def test_returns_base_when_free(self):
        with mock.patch.object(os_util, "tcp_port_is_free", return_value=True):
            listen_port = os_util.find_first_free_listen_port_after_base("127.0.0.1", 50000)
        assert listen_port == 50000

    def test_skips_until_first_free_port(self):
        with mock.patch.object(os_util, "tcp_port_is_free", side_effect=[False, False, True]):
            listen_port = os_util.find_first_free_listen_port_after_base("127.0.0.1", 50100)
        assert listen_port == 50102

    def test_skips_blocklisted_ports(self):
        with mock.patch.object(os_util, "tcp_port_is_free", return_value=True):
            listen_port = os_util.find_first_free_listen_port_after_base(
                "127.0.0.1",
                50200,
                blocklist=[50200],
            )
        assert listen_port == 50201

    def test_raises_when_scan_exhausted(self):
        with mock.patch.object(os_util, "tcp_port_is_free", return_value=False):
            with pytest.raises(ValueError, match="No free listen port"):
                os_util.find_first_free_listen_port_after_base("127.0.0.1", 50300, max_offset=2)
