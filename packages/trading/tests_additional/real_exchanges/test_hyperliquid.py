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
import time

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_trading.errors as trading_errors
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

MAX_FETCHTABLE_TIME = round(
    time.time() * commons_constants.MSECONDS_TO_SECONDS
    - (
        (commons_enums.TimeFramesMinutes[commons_enums.TimeFrames.ONE_HOUR] * commons_constants.MSECONDS_TO_MINUTE)
        * 1500
    )
)


class TestHyperliquidRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "hyperliquid"
    SYMBOL = "BTC/USDC"
    SYMBOL_2 = "ETH/USDC"
    SYMBOL_3 = "HYPE/USDC"
    CANDLE_SINCE = MAX_FETCHTABLE_TIME
    CANDLE_SINCE_SEC = CANDLE_SINCE / 1000

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
            commons_enums.TimeFrames.TWELVE_HOURS,
            commons_enums.TimeFrames.ONE_DAY,
            commons_enums.TimeFrames.THREE_DAYS,
            commons_enums.TimeFrames.ONE_WEEK,
            commons_enums.TimeFrames.ONE_MONTH,
        ])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(420, 470)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            has_price_limits=False,
            low_cost_min=10,
            low_cost_max=10,
            normal_cost_min=10,
            normal_cost_max=10,
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(
            tested_limit=200,
            default_min_length=1000,
        )

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv(cap_time_extra_seconds=self.get_timeframe_seconds() * 4)

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=20)
        await self.assert_order_book_custom_limit(
            50,
            supports_custom_limit=False,
            reference_no_limit_depth=20,
        )

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_recent_trades()

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_open=False,
                check_high=False,
                check_low=False,
                check_base_volume=False,
                check_quote_volume=True,
            )

        def _hyperliquid_price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                high=Te.NONE,
                low=Te.NONE,
                bid=Te.NONE,
                bid_volume=Te.NONE,
                ask=Te.NONE,
                ask_volume=Te.NONE,
                open=Te.NONE,
                previous_close=Te.TRUTHY,
                base_volume=Te.NONE,
                quote_volume=Te.TRUTHY,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
            ticker_expectations=_hyperliquid_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
