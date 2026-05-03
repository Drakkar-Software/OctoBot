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


_DAY_SECONDS = 86400


class TestHollaexRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "hollaex"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/USDT"
    TIME_FRAME = commons_enums.TimeFrames.ONE_DAY
    HISTORICAL_CANDLES_TO_FETCH_COUNT = 500

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_HOUR,
            commons_enums.TimeFrames.ONE_DAY,
        ])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(30, 30)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            normal_price_max=30000,
            normal_cost_min=1e-07,
            low_price_min=0.01,
            low_price_max=1,
            low_cost_min=0.01,
            low_cost_max=1,
            enable_price_and_cost_comparison=False,
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(
            default_min_length=1400,
            tested_limit=20,
        )

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv(
            max_candle_upper_time=lambda: self.get_time() + 500 * _DAY_SECONDS,
        )

    async def test_get_historical_ohlcv(self):
        historical_ohlcv = await self.get_historical_ohlcv()
        historical_len = len(historical_ohlcv)
        assert historical_len > 400, f"{historical_len=} <= 400"
        self.ensure_elements_order(historical_ohlcv, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        start, end = self.get_historical_ohlcv_start_and_end_times()
        max_candle_time = self.get_time_after_time_frames(start, len(historical_ohlcv))
        assert max_candle_time <= end + 2 * _DAY_SECONDS
        assert max_candle_time <= self.get_time()
        expected_count = self.HISTORICAL_CANDLES_TO_FETCH_COUNT
        assert (
            expected_count * 0.85
            < historical_len
            <= expected_count
        ), f"{historical_len=} not in [{expected_count * 0.85}:{expected_count}]"
        for candle in historical_ohlcv:
            open_time = candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
            assert start <= open_time <= end + 2 * _DAY_SECONDS, (
                f"daily streamed candle timestamp outside stretched window "
                f"({open_time=} {start=} {end=} slack={2 * _DAY_SECONDS})"
            )

    async def test_get_kline_price(self):
        await self.assert_get_kline_price(time_frame=commons_enums.TimeFrames.ONE_HOUR)

    async def test_get_order_book(self):
        await self.assert_get_order_book(
            limit=None,
            depth_mode="minimum",
            min_orders_per_side=10,
        )
        await self.assert_order_book_custom_limit(
            50,
            supports_custom_limit=False,
            reference_no_limit_depth=20,
        )

    async def test_get_order_books(self):
        await self.inner_test_get_order_books(
            False,
            30,
            20,
            0,
            False,
            None,
            15,
            True,
        )

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                bid=Te.NONE,
                ask=Te.NONE,
            )

        await self.assert_get_price_ticker(
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
