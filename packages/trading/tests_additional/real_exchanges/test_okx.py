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


class TestOkxRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "okx"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "OKB/BTC"

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_MINUTE,
            commons_enums.TimeFrames.THREE_MINUTES,
            commons_enums.TimeFrames.FIVE_MINUTES,
            commons_enums.TimeFrames.FIFTEEN_MINUTES,
            commons_enums.TimeFrames.THIRTY_MINUTES,
            commons_enums.TimeFrames.ONE_HOUR,
            commons_enums.TimeFrames.TWO_HOURS,
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
        await self.inner_test_active_symbols(2400, 2400)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            normal_cost_min=1e-09,
            low_cost_min=1e-08,
            has_price_limits=False,
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(default_limit=100, tested_limit=200)
        # max returned candles is 300 (differs from docs stating 100)
        symbol_prices = await self.get_symbol_prices(limit=1000)
        assert len(symbol_prices) == 300
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        assert symbol_prices[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value] >= (
            self.get_time() - self.get_allowed_time_delta()
        )

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv()

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=5, order_book_entry_length=3)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(ticker)

        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                bid_volume=Te.TRUTHY,
                ask_volume=Te.TRUTHY,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
