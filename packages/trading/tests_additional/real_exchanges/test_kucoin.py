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
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestKucoinRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "kucoin"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"

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
        await self.inner_test_active_symbols(1100, 1100)

    async def test_get_market_status(self):

        def extra_checks(market_status):
            # kucoin special value to handle to market status min cost (https://docs.kucoin.com/#get-symbols-list)
            min_funds = market_status[ccxt_constants.CCXT_INFO].get("minFunds")
            assert min_funds is not None
            assert float(min_funds) > 0

        # invalid values (should be much lower for XRP/BTC => remove price limit in tentacle
        await self.assert_get_market_status(
            has_price_limits=False,
            extra_checks=extra_checks
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices()

    async def test_get_historical_symbol_prices(self):
        await self.assert_get_historical_ohlcv()

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        await self.assert_get_kline_price()

    async def test_get_order_book(self):
        # kucoin requires a limit of None, 20 or 100 in order book
        await self.assert_get_order_book(limit=20)
        
    async def test_get_order_books(self):
        # not supported
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=20)

    async def test_get_price_ticker(self):
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker, check_open=False
            )
        
        await self.assert_get_price_ticker(
            extra_checks=extra_checks
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()
