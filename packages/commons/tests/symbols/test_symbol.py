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
import pytest

import octobot_commons.symbols
import octobot_commons.enums


@pytest.fixture
def spot_symbol():
    return octobot_commons.symbols.Symbol("BTC/USDT")


@pytest.fixture
def perpetual_future_symbol():
    return octobot_commons.symbols.Symbol("BTC/USDT:BTC")


@pytest.fixture
def future_symbol():
    return octobot_commons.symbols.Symbol("ETH/USDT:USDT-210625")


@pytest.fixture
def option_symbol():
    return octobot_commons.symbols.Symbol("ETH/USDT:USDT-211225-40000-C")


@pytest.fixture
def put_option_symbol():
    return octobot_commons.symbols.Symbol("BTC/USDT:BTC-211225-60000-P")


def test_parse_spot_symbol(spot_symbol):
    assert spot_symbol.base == "BTC"
    assert spot_symbol.quote == "USDT"
    assert spot_symbol.settlement_asset == spot_symbol.identifier == spot_symbol.strike_price == ""
    assert spot_symbol.option_type is None


def test_parse_perpetual_future_symbol(perpetual_future_symbol):
    assert perpetual_future_symbol.base == "BTC"
    assert perpetual_future_symbol.quote == "USDT"
    assert perpetual_future_symbol.settlement_asset == "BTC"
    assert perpetual_future_symbol.strike_price == ""
    assert perpetual_future_symbol.option_type is None


def test_parse_future_symbol(future_symbol):
    assert future_symbol.base == "ETH"
    assert future_symbol.quote == "USDT"
    assert future_symbol.settlement_asset == "USDT"
    assert future_symbol.identifier == "210625"
    assert future_symbol.strike_price == ""
    assert future_symbol.option_type is None


def test_parse_option_symbol(option_symbol):
    assert option_symbol.base == "ETH"
    assert option_symbol.quote == "USDT"
    assert option_symbol.settlement_asset == "USDT"
    assert option_symbol.identifier == "211225"
    assert option_symbol.strike_price == "40000"
    assert option_symbol.option_type == octobot_commons.enums.OptionTypes.CALL.value


def test_base_and_quote(spot_symbol, option_symbol):
    assert spot_symbol.base_and_quote() == ("BTC", "USDT")
    assert option_symbol.base_and_quote() == ("ETH", "USDT")


def test_is_linear(spot_symbol, perpetual_future_symbol,  option_symbol):
    assert spot_symbol.is_linear() is True
    assert perpetual_future_symbol.is_linear() is False
    assert option_symbol.is_linear() is True


def test_is_inverse(spot_symbol, perpetual_future_symbol, option_symbol):
    assert spot_symbol.is_inverse() is False
    assert perpetual_future_symbol.is_inverse() is True
    assert option_symbol.is_inverse() is False


def test_merged_str_symbol_with_full_option(option_symbol, put_option_symbol):
    call_symbol = octobot_commons.symbols.Symbol("ETH/USDT:USDT-211225-40000-C")
    call_symbol.option_type = octobot_commons.enums.OptionTypes.CALL.value
    call_symbol.strike_price = 40000
    call_symbol.identifier = "211225"
    assert call_symbol.merged_str_symbol() == "ETH/USDT:USDT-211225-40000-C"
    
    put_symbol = octobot_commons.symbols.Symbol("BTC/USDT:BTC-211225-60000-P")
    put_symbol.option_type = octobot_commons.enums.OptionTypes.PUT.value
    put_symbol.strike_price = 60000
    put_symbol.identifier = "211225"
    assert put_symbol.merged_str_symbol() == "BTC/USDT:BTC-211225-60000-P"

    custom_symbol = octobot_commons.symbols.Symbol("BTC/USDT:BTC-211225-60000-yES")
    custom_symbol.option_type = "YES"
    custom_symbol.strike_price = 60000
    custom_symbol.identifier = "211225"
    assert custom_symbol.merged_str_symbol() == "BTC/USDT:BTC-211225-60000-YES"


def test_is_put_option():
    put_symbol = octobot_commons.symbols.Symbol("BTC/USDT:BTC-211225-60000-P")
    assert put_symbol.is_put_option() is True
    assert put_symbol.is_call_option() is False


def test_is_call_option():
    call_symbol = octobot_commons.symbols.Symbol("ETH/USDT:USDT-211225-40000-C")
    assert call_symbol.is_call_option() is True
    assert call_symbol.is_put_option() is False


def test_is_put_and_call_option_with_non_option_symbols(spot_symbol, perpetual_future_symbol, future_symbol):
    assert spot_symbol.is_put_option() is False
    assert spot_symbol.is_call_option() is False
    assert perpetual_future_symbol.is_put_option() is False
    assert perpetual_future_symbol.is_call_option() is False
    assert future_symbol.is_put_option() is False
    assert future_symbol.is_call_option() is False


def test_does_expire(spot_symbol, perpetual_future_symbol, future_symbol, option_symbol, put_option_symbol):
    assert spot_symbol.does_expire() is False
    assert perpetual_future_symbol.does_expire() is False
    assert future_symbol.does_expire() is True
    assert option_symbol.does_expire() is True
    assert put_option_symbol.does_expire() is True


def test__eq__(spot_symbol, option_symbol):
    assert spot_symbol == octobot_commons.symbols.Symbol("BTC/USDT")
    assert spot_symbol != octobot_commons.symbols.Symbol("BTC/USD")
    assert spot_symbol != option_symbol
    assert option_symbol == octobot_commons.symbols.Symbol("ETH/USDT:USDT-211225-40000-C")
    assert option_symbol != octobot_commons.symbols.Symbol("ETH/USDT:USDT-211225-40000-P")
