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
import ccxt.async_support as ccxt_async

import octobot_commons.enums as commons_enums
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBithumbRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "bithumb"
    SYMBOL = "BTC/KRW"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"

    async def test_time_frames(self):
        await self.assert_time_frames([
            commons_enums.TimeFrames.ONE_MINUTE,
            commons_enums.TimeFrames.THREE_MINUTES,
            commons_enums.TimeFrames.FIVE_MINUTES,
            commons_enums.TimeFrames.THIRTY_MINUTES,
            commons_enums.TimeFrames.ONE_HOUR,
            commons_enums.TimeFrames.SIX_HOURS,
            commons_enums.TimeFrames.TWELVE_HOURS,
            commons_enums.TimeFrames.ONE_DAY,
        ])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(450, 450)

    async def test_get_market_status(self):
        await self.assert_get_market_status(has_price_limits=False)

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(
            default_min_length = 4000
        )

    async def test_get_historical_symbol_prices(self):
        for limit in (50, None):
            symbol_prices = await self.get_symbol_prices(since=self.CANDLE_SINCE, limit=limit)
            if limit:
                assert len(symbol_prices) == limit
            else:
                assert len(symbol_prices) > 5
            self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
            max_candle_time = self.get_time_after_time_frames(self.CANDLE_SINCE_SEC, len(symbol_prices))
            assert max_candle_time <= self.get_time()
            with pytest.raises(AssertionError):
                for candle in symbol_prices:
                    assert (
                        self.CANDLE_SINCE_SEC
                        <= candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                        <= max_candle_time
                    )

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=5)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

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
