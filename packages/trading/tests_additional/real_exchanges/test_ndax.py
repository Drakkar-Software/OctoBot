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
import octobot_trading.errors as errors
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestNdaxRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "ndax"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/CAD"
    SYMBOL_3 = "XRP/CAD"
    INACTIVE_MARKETS = [SYMBOL]
    TIME_FRAME = commons_enums.TimeFrames.ONE_DAY

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_MINUTE,
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

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(70, 70)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            low_price_max=1e-03,
            low_price_min=1e-05,
            normal_cost_min=1e-07,
            low_cost_max=1e-02,
            low_cost_min=1e-04,
            enable_price_and_cost_comparison=False,
        )

    async def test_get_symbol_prices(self):
        # NDAX returns no rows when limit is omitted; explicit limit works.
        await self.assert_get_symbol_prices_empty_default_then_limit(tested_limit=200)

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv(
            max_candle_upper_time=lambda: self.get_time() + 7 * 86400,
        )

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        # Shallow book (each side 0–5 rows); entries include order ids (three columns).
        await self.assert_get_order_book(
            limit=None,
            depth_mode="range",
            min_orders_per_side=0,
            max_orders_per_side=5,
            order_book_entry_length=3,
            allow_empty_book_side=True,
        )

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_high=False,
                check_low=False,
                check_open=False,
            )

        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                high=Te.NONE,
                low=Te.NONE,
                ask=Te.NONE,
                open=Te.NONE,
                base_volume=Te.NOT_NONE,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        with pytest.raises(errors.NotSupported):
            await self.get_all_currencies_price_ticker()
