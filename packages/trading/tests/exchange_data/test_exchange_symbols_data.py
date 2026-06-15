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
import pytest
import pytest_asyncio

import octobot_commons.enums as commons_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
from octobot_trading.exchange_data.exchange_symbols_data import ExchangeSymbolsData

# Import required fixtures
from tests import event_loop
from tests.exchanges import exchange_manager

pytestmark = pytest.mark.asyncio

DEFAULT_SYMBOL = "BTC/USDT"
SECOND_SYMBOL = "ETH/USDT"


def _build_exchange_data(markets):
    return exchange_data_import.ExchangeData(markets=markets)


def _build_market_details(
    symbol,
    time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
    *,
    close=None,
    open_=None,
    high=None,
    low=None,
    volume=None,
    time=None,
):
    return exchange_data_import.MarketDetails(
        symbol=symbol,
        time_frame=time_frame,
        close=close if close is not None else [100.0],
        open=open_ if open_ is not None else [99.0],
        high=high if high is not None else [101.0],
        low=low if low is not None else [98.0],
        volume=volume if volume is not None else [10.0],
        time=time if time is not None else [1_000.0],
    )


@pytest_asyncio.fixture(scope="function")
async def exchange_symbols_data(exchange_manager):
    return ExchangeSymbolsData(exchange_manager)


async def test_get_exchange_symbol_data(exchange_symbols_data):
    new_symbols_data = exchange_symbols_data.get_exchange_symbol_data("BTC/USDT")
    assert new_symbols_data is not None
    assert exchange_symbols_data.get_exchange_symbol_data("BTC/USDT") is new_symbols_data


async def test_get_exchange_symbol_data_without_creation(exchange_symbols_data):
    with pytest.raises(KeyError):
        exchange_symbols_data.get_exchange_symbol_data("BTC/USDT", allow_creation=False)
    exchange_symbols_data.get_exchange_symbol_data("ETH/USDT", allow_creation=True)
    with pytest.raises(KeyError):
        exchange_symbols_data.get_exchange_symbol_data("ETH/BTC", allow_creation=False)


class TestExchangeSymbolsDataInitializeCandlesFromExchangeData:
    async def test_does_nothing_when_no_markets(self, exchange_symbols_data):
        await exchange_symbols_data.initialize_candles_from_exchange_data(_build_exchange_data([]))
        assert exchange_symbols_data.exchange_symbol_data == {}

    async def test_skips_market_without_time_frame(self, exchange_symbols_data):
        market = _build_market_details(DEFAULT_SYMBOL, time_frame="")
        await exchange_symbols_data.initialize_candles_from_exchange_data(_build_exchange_data([market]))
        assert DEFAULT_SYMBOL not in exchange_symbols_data.exchange_symbol_data

    async def test_skips_market_without_full_candles(self, exchange_symbols_data):
        market = _build_market_details(DEFAULT_SYMBOL, open_=[])
        await exchange_symbols_data.initialize_candles_from_exchange_data(_build_exchange_data([market]))
        assert DEFAULT_SYMBOL not in exchange_symbols_data.exchange_symbol_data

    async def test_loads_candles_for_valid_market(self, exchange_symbols_data):
        expected_close = 123.0
        market = _build_market_details(DEFAULT_SYMBOL, close=[expected_close])
        await exchange_symbols_data.initialize_candles_from_exchange_data(_build_exchange_data([market]))
        symbol_data = exchange_symbols_data.get_exchange_symbol_data(DEFAULT_SYMBOL, allow_creation=False)
        candles_manager = symbol_data.symbol_candles[commons_enums.TimeFrames.ONE_HOUR]
        assert candles_manager.close_candles[0] == expected_close

    async def test_only_processes_valid_markets_in_mixed_list(self, exchange_symbols_data):
        skipped_market = _build_market_details(DEFAULT_SYMBOL, time_frame="")
        expected_close = 456.0
        valid_market = _build_market_details(SECOND_SYMBOL, close=[expected_close])
        await exchange_symbols_data.initialize_candles_from_exchange_data(
            _build_exchange_data([skipped_market, valid_market])
        )
        assert DEFAULT_SYMBOL not in exchange_symbols_data.exchange_symbol_data
        symbol_data = exchange_symbols_data.get_exchange_symbol_data(SECOND_SYMBOL, allow_creation=False)
        candles_manager = symbol_data.symbol_candles[commons_enums.TimeFrames.ONE_HOUR]
        assert candles_manager.close_candles[0] == expected_close
