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
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestKucoinEuRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "kucoineu"
    SYMBOL = "BTC/USDC"
    SYMBOL_2 = "ETH/USDC"
    SYMBOL_3 = "ADA/USDC"

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
            commons_enums.TimeFrames.HEIGHT_HOURS,
            commons_enums.TimeFrames.TWELVE_HOURS,
            commons_enums.TimeFrames.ONE_DAY,
            commons_enums.TimeFrames.ONE_WEEK,
        ])

    async def test_supports_order_type(self):
        await self.assert_supports_order_type(
            real_exchange_tester.ORDER_TYPES_WITH_STOP_LOSS
        )

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(767, 767)

    async def test_get_market_status(self):

        def extra_checks(market_status):
            min_funds = market_status[ccxt_constants.CCXT_INFO].get("minFunds")
            assert min_funds is not None
            assert float(min_funds) > 0

        await self.assert_get_market_status(
            has_price_limits=False,
            low_cost_max=10,
            extra_checks=extra_checks
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(
            default_allowed_lengths=(8, 100),
            tested_limit=100,
            tested_limit_min=8,
            expect_recent_last_candle=False,
        )

    async def test_get_historical_symbol_prices(self):
        symbol_prices = await self.get_symbol_prices(limit=100)
        assert symbol_prices is not None
        assert len(symbol_prices) > 0

    async def test_get_historical_ohlcv(self):
        symbol_prices = await self.get_symbol_prices(limit=100)
        assert symbol_prices is not None
        assert len(symbol_prices) > 0
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)

    async def test_get_kline_price(self):
        kline_price = await self.get_kline_price()
        assert kline_price is not None
        if kline_price:
            assert len(kline_price) == 1
            assert len(kline_price[0]) == 6

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=20)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        recent_trades = await self.get_recent_trades(limit=20)
        assert len(recent_trades) <= 20
        if recent_trades:
            self.ensure_elements_order(
                recent_trades, trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value
            )

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker, check_open=False, check_high=False, check_low=False
            )

        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                high=Te.SKIP,
                low=Te.SKIP,
                open=Te.SKIP,
                base_volume=Te.SKIP,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
