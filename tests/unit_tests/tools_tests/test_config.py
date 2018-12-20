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

from config.config import load_config


def test_load_config():
    result = load_config("tests/static/config.json")
    assert "crypto-currencies" in result
    assert "services" in result
    assert "exchanges" in result
    assert "trading" in result
    assert "Bitcoin" in result["crypto-currencies"]


def test_load_config_without_file(caplog):
    load_config("tests/static/test_config.json", error=False)
    assert 'file opening failed' in caplog.text


def test_load_config_incorrect(caplog):
    load_config("tests/unit_tests/tools_tests/incorrect_config_file.txt", error=False)
    assert 'json decoding failed' in caplog.text
