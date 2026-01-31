#  Drakkar-Software OctoBot-Trading
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
import decimal
import mock
import pytest

import octobot_trading.modes.script_keywords as script_keywords


def test_parse_quantity_types():
    assert script_keywords.parse_quantity(None) == (script_keywords.QuantityType.DELTA, None)
    assert script_keywords.parse_quantity(10) == (script_keywords.QuantityType.DELTA, decimal.Decimal(10))
    assert script_keywords.parse_quantity(-10) == (script_keywords.QuantityType.DELTA, decimal.Decimal(-10))
    assert script_keywords.parse_quantity(1.366666663347877) == \
           (script_keywords.QuantityType.DELTA, decimal.Decimal("1.366666663347877"))
    assert script_keywords.parse_quantity("-10") == (script_keywords.QuantityType.DELTA, decimal.Decimal(-10))

    assert script_keywords.parse_quantity("-10d") == (script_keywords.QuantityType.DELTA_EXPLICIT, decimal.Decimal(-10))
    assert script_keywords.parse_quantity("d-10") == (script_keywords.QuantityType.DELTA_EXPLICIT, decimal.Decimal(-10))
    assert script_keywords.parse_quantity("d+10") == (script_keywords.QuantityType.DELTA_EXPLICIT, decimal.Decimal(10))
    assert script_keywords.parse_quantity("d10") == (script_keywords.QuantityType.DELTA_EXPLICIT, decimal.Decimal(10))

    assert script_keywords.parse_quantity("-10b") == (script_keywords.QuantityType.DELTA_BASE, decimal.Decimal(-10))

    assert script_keywords.parse_quantity("q") == (script_keywords.QuantityType.DELTA_QUOTE, None)
    assert script_keywords.parse_quantity("123q") == (
        script_keywords.QuantityType.DELTA_QUOTE, decimal.Decimal("123"))
    assert script_keywords.parse_quantity("q-0.11") == (
        script_keywords.QuantityType.DELTA_QUOTE, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("%") == (script_keywords.QuantityType.PERCENT, None)
    assert script_keywords.parse_quantity("99.5%") == (
        script_keywords.QuantityType.PERCENT, decimal.Decimal("99.5"))
    assert script_keywords.parse_quantity("-0.11%") == (
        script_keywords.QuantityType.PERCENT, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("a%") == (script_keywords.QuantityType.AVAILABLE_PERCENT, None)
    assert script_keywords.parse_quantity("-0.11a%") == (
        script_keywords.QuantityType.AVAILABLE_PERCENT, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("%a-0.11") == (
        script_keywords.QuantityType.AVAILABLE_PERCENT, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("a") == (script_keywords.QuantityType.AVAILABLE, None)
    assert script_keywords.parse_quantity("-0.11a") == (
        script_keywords.QuantityType.AVAILABLE, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("a-0.11") == (
        script_keywords.QuantityType.AVAILABLE, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("e%") == (script_keywords.QuantityType.ENTRY_PERCENT, None)
    assert script_keywords.parse_quantity("-0.11e%") == (
        script_keywords.QuantityType.ENTRY_PERCENT, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("-0.11%e") == (
        script_keywords.QuantityType.ENTRY_PERCENT, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("e") == (script_keywords.QuantityType.ENTRY, None)
    assert script_keywords.parse_quantity("-0.11e") == (
        script_keywords.QuantityType.ENTRY, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("e-0.11") == (
        script_keywords.QuantityType.ENTRY, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("p%") == (script_keywords.QuantityType.POSITION_PERCENT, None)
    assert script_keywords.parse_quantity("%p") == (script_keywords.QuantityType.POSITION_PERCENT, None)
    assert script_keywords.parse_quantity("-0.11p%") == (
        script_keywords.QuantityType.POSITION_PERCENT, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("-0.11p") == (
        script_keywords.QuantityType.POSITION_PERCENT_ALIAS, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("%p-0.11") == (
        script_keywords.QuantityType.POSITION_PERCENT, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("p") == (script_keywords.QuantityType.POSITION_PERCENT_ALIAS, None)
    assert script_keywords.parse_quantity("-0.11p") == (
        script_keywords.QuantityType.POSITION_PERCENT_ALIAS, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("p-0.11") == (
        script_keywords.QuantityType.POSITION_PERCENT_ALIAS, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("@") == (script_keywords.QuantityType.FLAT, None)
    assert script_keywords.parse_quantity("-0.11@") == (script_keywords.QuantityType.FLAT, decimal.Decimal("-0.11"))
    assert script_keywords.parse_quantity("@-0.11") == (script_keywords.QuantityType.FLAT, decimal.Decimal("-0.11"))

    assert script_keywords.parse_quantity("wyz-0.11") == (script_keywords.QuantityType.UNKNOWN, None)
    assert script_keywords.parse_quantity("wyz12") == (script_keywords.QuantityType.UNKNOWN, None)
    assert script_keywords.parse_quantity("wyz") == (script_keywords.QuantityType.UNKNOWN, None)


def test_parse_quantity_edge_numbers():
    assert script_keywords.parse_quantity(0) == (script_keywords.QuantityType.DELTA, decimal.Decimal(0))
    assert script_keywords.parse_quantity(0.000000001) == \
           (script_keywords.QuantityType.DELTA, decimal.Decimal("0.000000001"))
    assert script_keywords.parse_quantity(100000000000000000000) \
           == (script_keywords.QuantityType.DELTA, decimal.Decimal("100000000000000000000"))
    assert script_keywords.parse_quantity("100000000000000000000b") \
           == (script_keywords.QuantityType.DELTA_BASE, decimal.Decimal("100000000000000000000"))
    assert script_keywords.parse_quantity("-1e-09e%") == (
        script_keywords.QuantityType.ENTRY_PERCENT, decimal.Decimal("-1e-09"))
    assert script_keywords.parse_quantity("1e09%e") == (
        script_keywords.QuantityType.ENTRY_PERCENT, decimal.Decimal("1e09"))
    assert script_keywords.parse_quantity("1e9e") == (script_keywords.QuantityType.ENTRY, decimal.Decimal("1e9"))
    with mock.patch.object(script_keywords.QuantityType, "parse",
                           mock.Mock(return_value=(script_keywords.QuantityType.ENTRY, "e"))):
        with pytest.raises(RuntimeError):
            script_keywords.parse_quantity("0.000000001aa")
