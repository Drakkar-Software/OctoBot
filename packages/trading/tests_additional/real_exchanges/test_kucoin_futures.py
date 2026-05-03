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

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester
from tests_additional.real_exchanges.real_futures_exchange_tester import RealFuturesExchangeTester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestKucoinFuturesRealExchangeTester(RealFuturesExchangeTester):
    EXCHANGE_NAME = "kucoinfutures"
    SYMBOL = "BTC/USDT:USDT"
    SYMBOL_2 = "BTC/USD:BTC"
    SYMBOL_3 = "XRP/USD:XRP"
    CANDLE_SINCE = 1722823200000    # Monday, August 5, 2024 2:00:00 AM
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
            commons_enums.TimeFrames.SIX_HOURS,
            commons_enums.TimeFrames.HEIGHT_HOURS,
            commons_enums.TimeFrames.TWELVE_HOURS,
            commons_enums.TimeFrames.ONE_DAY,
            commons_enums.TimeFrames.ONE_WEEK,
        ])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(450, 450)

    async def test_get_market_status(self):
        await self.assert_market_status()
        for market_status in await self.get_market_statuses():
            # ensure no "minFunds" in futures
            assert "minFunds" not in market_status[ccxt_constants.CCXT_INFO]

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(default_limit=200, tested_limit=100)

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv()

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        await self.assert_get_order_book(limit=20)
        
    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_open=False,
                check_low=False,
                check_high=False,
                check_base_volume=False,
            )

        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                high=Te.NONE,
                low=Te.NONE,
                bid=Te.TRUTHY,
                bid_volume=Te.TRUTHY,
                ask=Te.TRUTHY,
                ask_volume=Te.TRUTHY,
                open=Te.NONE,
                previous_close=Te.NONE,
                base_volume=Te.NONE,
                timestamp=Te.TRUTHY,
            )

        await self.assert_get_price_ticker(
            extra_checks=extra_checks,
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()

    async def test_get_funding_rate(self):
        await self.assert_get_funding_rate(funding_info_in_ticker=False)
