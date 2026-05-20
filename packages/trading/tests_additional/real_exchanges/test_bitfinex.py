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


class TestBitfinexRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "bitfinex"
    SYMBOL = "BTC/USD"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"
    DEFAULT_CANDLE_LIMIT = 500

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_MINUTE,
            commons_enums.TimeFrames.FIVE_MINUTES,
            commons_enums.TimeFrames.FIFTEEN_MINUTES,
            commons_enums.TimeFrames.THIRTY_MINUTES,
            commons_enums.TimeFrames.ONE_HOUR,
            commons_enums.TimeFrames.FOUR_HOURS,
            commons_enums.TimeFrames.SIX_HOURS,
            commons_enums.TimeFrames.TWELVE_HOURS,
            commons_enums.TimeFrames.ONE_DAY,
            commons_enums.TimeFrames.ONE_WEEK,
            commons_enums.TimeFrames.ONE_MONTH,
        ])

    async def test_supports_order_type(self):
        await self.assert_supports_order_type()

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(280, 280)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            normal_price_min=1e-08,
            normal_cost_min=1e-13,
            low_cost_min=1e-08,
            enable_price_and_cost_comparison=False,
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(
            default_allowed_lengths=(100, 10_000),
            expect_recent_last_candle=False,
        )

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv(
            require_each_open_time_not_before_since=False,
            candle_upper_slack_seconds=self.get_timeframe_seconds() * 200,
        )

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price(require_recent_open_time=False)

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=25)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
