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
import octobot_commons.databases as databases


def test_remove_oldest_elements():
    databases.GlobalSharedMemoryStorage.instance()["10"] = "a"
    databases.GlobalSharedMemoryStorage.instance()["2"] = 1
    databases.GlobalSharedMemoryStorage.instance()["-1"] = "af"
    databases.GlobalSharedMemoryStorage.instance()["0"] = "as"
    databases.GlobalSharedMemoryStorage.instance()[10] = "asfgvfs"
    databases.GlobalSharedMemoryStorage.instance()["12"] = "bbcc"
    assert len(databases.GlobalSharedMemoryStorage.instance()) == 6
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "10": "a",
        "2": 1,
        "-1": "af",
        "0": "as",
        10: "asfgvfs",
        "12": "bbcc",
    }
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(0)
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "10": "a",
        "2": 1,
        "-1": "af",
        "0": "as",
        10: "asfgvfs",
        "12": "bbcc",
    }
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(1)
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "2": 1,
        "-1": "af",
        "0": "as",
        10: "asfgvfs",
        "12": "bbcc",
    }
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(4)
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "12": "bbcc",
    }
    databases.GlobalSharedMemoryStorage.instance()["2"] = 1
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "12": "bbcc",
        "2": 1,
    }
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(1)
    assert databases.GlobalSharedMemoryStorage.instance() == {
        "2": 1,
    }
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(10)
    assert databases.GlobalSharedMemoryStorage.instance() == {}


def test_get_bytes_size():
    assert 0 < databases.GlobalSharedMemoryStorage.instance().get_bytes_size() < 1000
    for i in range(10000):
        databases.GlobalSharedMemoryStorage.instance()[i] = "aaaaaaaaaaaaaaaaaaaaaa"
    assert 200000 < databases.GlobalSharedMemoryStorage.instance().get_bytes_size() < 800000
    databases.GlobalSharedMemoryStorage.instance().remove_oldest_elements(10000)
