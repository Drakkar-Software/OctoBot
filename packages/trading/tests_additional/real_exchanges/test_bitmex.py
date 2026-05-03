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

import octobot_commons.enums as commons_enums
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBitmexRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "bitmex"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "BONK/USDT"

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_MINUTE,
            commons_enums.TimeFrames.FIVE_MINUTES,
            commons_enums.TimeFrames.ONE_HOUR,
            commons_enums.TimeFrames.ONE_DAY,
        ])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(100, 100)

    async def test_get_market_status(self):
        await self.assert_get_market_status()

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(default_limit=100, tested_limit=200)

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv()

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        await self.assert_get_order_book(
            limit=None,
            depth_mode="minimum",
            min_orders_per_side=5,
        )

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(ticker)

        await self.assert_get_price_ticker(extra_checks=extra_checks)

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
