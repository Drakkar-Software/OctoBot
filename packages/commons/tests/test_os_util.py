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
import octobot_commons.os_util as os_util


def test_get_cpu_and_ram_usage():
    cpu, percent_ram, used_ram, process_ram, virtual_ram, unique_ram = os_util.get_cpu_and_ram_usage(0.1)
    assert isinstance(cpu, float)
    assert percent_ram > 0
    assert used_ram > 0
    assert process_ram > 0
    assert virtual_ram > 0
    assert unique_ram > 0
