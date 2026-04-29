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

import mock
import pytest

import octobot_commons.constants
import octobot_commons.symbols
import octobot_trading.exchange_data as exchange_data


@pytest.fixture
def ticker_cache():
    cache = exchange_data.TickerCache(ttl=3600, maxsize=50)
    yield cache
    cache.reset_all_tickers_cache()


SPOT_TICKERS = {
    "BTC/USDT": mock.Mock(),
    "ETH/USDT": mock.Mock(),
    "SOL/USDT": mock.Mock(),
}

FUTURES_TICKERS = {
    "BTC/USDT:USDT": mock.Mock(),
    "ETH/USDT:USDT": mock.Mock(),
    "SOL/USD:SOL": mock.Mock(),
}


def test_is_valid_symbol(ticker_cache):
    ticker_cache.set_all_tickers("binance", "spot", False, SPOT_TICKERS)
    assert ticker_cache.is_valid_symbol("binance", "spot", False, "BTC/USDT") is True
    assert ticker_cache.is_valid_symbol("binance", "spot", False, "BTC2/USDT") is False
    assert ticker_cache.is_valid_symbol("binance", "futures", False, "BTC/USDT:USDT") is False
    ticker_cache.set_all_tickers("binance", "futures", False, FUTURES_TICKERS)
    assert ticker_cache.is_valid_symbol("binance", "futures", False, "BTC/USDT:USDT") is True
    ticker_cache.reset_all_tickers_cache()
    assert ticker_cache.is_valid_symbol("binance", "futures", False, "BTC/USDT:USDT") is False


def test_get_all_tickers(ticker_cache):
    assert ticker_cache.get_all_tickers("binance", "spot", False) is None
    assert ticker_cache.get_all_tickers("binance", "spot", False, "default") == "default"
    ticker_cache.set_all_tickers("binance", "spot", False, SPOT_TICKERS)
    assert ticker_cache.get_all_tickers("binance", "spot", False) == SPOT_TICKERS
    assert ticker_cache.get_all_tickers("binance", "spot", True) is None
    assert ticker_cache.get_all_tickers("binance", octobot_commons.constants.CONFIG_EXCHANGE_FUTURE, False) is None


def test_has_ticker_data(ticker_cache):
    assert ticker_cache.has_ticker_data("binance", "spot", False) is False
    ticker_cache.set_all_tickers("binance", "spot", False, SPOT_TICKERS)
    assert ticker_cache.has_ticker_data("binance", "spot", False) is True
    assert ticker_cache.has_ticker_data("binance", "spot", True) is False

    ticker_cache.reset_all_tickers_cache()
    assert ticker_cache.has_ticker_data("binance", "spot", False) is False


def test_get_all_parsed_symbols_by_merged_symbols(ticker_cache):
    assert ticker_cache.get_all_parsed_symbols_by_merged_symbols("binance", "spot", False) is None
    ticker_cache.set_all_tickers("binance", "spot", False, SPOT_TICKERS)
    assert ticker_cache.get_all_parsed_symbols_by_merged_symbols("binance", "spot", False) == {
        "BTCUSDT": octobot_commons.symbols.parse_symbol("BTC/USDT"),
        "ETHUSDT": octobot_commons.symbols.parse_symbol("ETH/USDT"),
        "SOLUSDT": octobot_commons.symbols.parse_symbol("SOL/USDT"),
    }
    assert ticker_cache.get_all_parsed_symbols_by_merged_symbols(
        "binance", octobot_commons.constants.CONFIG_EXCHANGE_FUTURE, False
    ) is None

    ticker_cache.set_all_tickers(
        "binance", octobot_commons.constants.CONFIG_EXCHANGE_FUTURE, False, FUTURES_TICKERS
    )
    assert ticker_cache.get_all_parsed_symbols_by_merged_symbols(
        "binance", octobot_commons.constants.CONFIG_EXCHANGE_FUTURE, False
    ) == {
        "BTCUSDT": octobot_commons.symbols.parse_symbol("BTC/USDT:USDT"),
        "BTCUSDT:USDT": octobot_commons.symbols.parse_symbol("BTC/USDT:USDT"),
        "ETHUSDT": octobot_commons.symbols.parse_symbol("ETH/USDT:USDT"),
        "ETHUSDT:USDT": octobot_commons.symbols.parse_symbol("ETH/USDT:USDT"),
        "SOLUSD": octobot_commons.symbols.parse_symbol("SOL/USD:SOL"),
        "SOLUSD:SOL": octobot_commons.symbols.parse_symbol("SOL/USD:SOL"),
    }

    assert ticker_cache.get_all_parsed_symbols_by_merged_symbols(
        "binance", octobot_commons.constants.CONFIG_EXCHANGE_FUTURE, True
    ) is None


def test_get_exchange_key():
    assert exchange_data.TickerCache.get_exchange_key("binance", "spot", True) == "binance_spot_True"
    assert exchange_data.TickerCache.get_exchange_key("binance", "spot", False) == "binance_spot_False"
    assert exchange_data.TickerCache.get_exchange_key("binance", "future", False) == "binance_future_False"
    assert exchange_data.TickerCache.get_exchange_key("okx", "future", False) == "okx_future_False"
