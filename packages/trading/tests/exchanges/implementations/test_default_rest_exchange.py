# pylint: disable=E0611
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
import octobot_trading.exchanges as exchanges
import octobot_commons.enums as commons_enums
import pytest

from tests.exchanges import exchange_manager, DEFAULT_EXCHANGE_NAME, MockedRestExchange

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def default_rest_exchange(exchange_manager):
    return MockedRestExchange(exchange_manager.config, exchange_manager, None)


async def test_start_request_data_and_stop(default_rest_exchange):
    await default_rest_exchange.initialize()
    symbol = "BTC/USDT"
    try:
        assert len(default_rest_exchange.symbols) > 10
        assert len(default_rest_exchange.time_frames) > 5
        market_status = default_rest_exchange.get_market_status(symbol)
        assert isinstance(market_status, dict)
        assert market_status
        ohlcv = await default_rest_exchange.get_symbol_prices(symbol, commons_enums.TimeFrames.ONE_HOUR)
        assert isinstance(ohlcv, list)
        assert len(ohlcv) > 50
        trades = await default_rest_exchange.get_recent_trades(symbol)
        assert isinstance(trades, list)
        assert len(trades) > 5
        ticker = await default_rest_exchange.get_price_ticker(symbol)
        assert isinstance(ticker, dict)
        assert ticker
        book = await default_rest_exchange.get_order_book(symbol)
        assert isinstance(book, dict)
        assert book
    finally:
        await default_rest_exchange.stop()
