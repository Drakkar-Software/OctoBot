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
import decimal

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester
from tests_additional.real_exchanges.real_futures_exchange_tester import RealFuturesExchangeTester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBybitRealExchangeTester(RealFuturesExchangeTester):
    EXCHANGE_NAME = "bybit"
    SYMBOL = "BTC/USDT:USDT"
    SYMBOL_2 = "ETH/USD:ETH"
    SYMBOL_3 = "XRP/USD:XRP"

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
        await self.assert_supports_order_type(
            real_exchange_tester.ORDER_TYPES_WITH_STOP_LOSS
        )

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(2400, 2400)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            low_price_min=0.0001,    # XRP/USD
            low_price_max=0.1,       # XRP/USD
            expect_inferior_or_equal_price_and_cost=True,
        )

    async def test_get_symbol_prices(self):
        await self.assert_get_symbol_prices(default_limit=200, tested_limit=200)

        # fetching more than 200 candles is fetching candles from the past
        symbol_prices = await self.get_symbol_prices(limit=1500)
        assert symbol_prices is not None
        assert len(symbol_prices) == 1000
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
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
        await self.assert_get_order_book(limit=5)
        
    async def test_get_order_books(self):
        # not supported
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        await self.assert_get_recent_trades(limit=50)

    async def test_get_price_ticker(self):
        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            Te = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                bid=Te.TRUTHY,
                bid_volume=Te.TRUTHY,
                ask=Te.TRUTHY,
                ask_volume=Te.TRUTHY,
                previous_close=Te.NONE,
                timestamp=Te.TRUTHY,
            )

        await self.assert_get_price_ticker(
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        await self.assert_get_all_currencies_price_ticker()

    async def test_get_funding_rate(self):
        await self.assert_get_funding_rate(funding_info_in_ticker=False, has_last_time=False)
        _, ticker_funding_rate = await self.get_funding_rate()
        ticker_funding = self._get_adapted_funding_from_ticker(ticker_funding_rate)
        self._check_funding_rate(ticker_funding)

    def _get_adapted_funding_from_ticker(self, ticker):
        tentacle_funding_from_ticker = {}
        funding_dict = ticker[ccxt_constants.CCXT_INFO]
        funding_next_timestamp = (
            float(funding_dict.get(ccxt_enums.ExchangeFundingCCXTColumns.NEXT_FUNDING_TIME.value, 0)) /
            commons_constants.MSECONDS_TO_SECONDS
        )
        funding_rate = decimal.Decimal(
            str(funding_dict.get(ccxt_enums.ExchangeFundingCCXTColumns.FUNDING_RATE.value, constants.NaN))
        )
        tentacle_funding_from_ticker.update({
            enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                max(funding_next_timestamp - 8 * commons_constants.HOURS_TO_SECONDS, 0),
            enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value: funding_rate,
            enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value: funding_next_timestamp,
            enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value: funding_rate
        })
        return tentacle_funding_from_ticker
