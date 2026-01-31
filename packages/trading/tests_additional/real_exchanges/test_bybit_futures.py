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

from octobot_commons.enums import TimeFrames, PriceIndexes
import octobot_commons.constants as commons_constants
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsOrderBookInfoColumns as Ecobic, ExchangeConstantsOrderColumns as Ecoc, \
    ExchangeConstantsTickersColumns as Ectc
from tests_additional.real_exchanges.real_futures_exchange_tester import RealFuturesExchangeTester
# required to catch async loop context exceptions
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBybitRealExchangeTester(RealFuturesExchangeTester):
    EXCHANGE_NAME = "bybit"
    SYMBOL = "BTC/USDT:USDT"
    SYMBOL_2 = "ETH/USD:ETH"
    SYMBOL_3 = "XRP/USD:XRP"

    async def test_time_frames(self):
        time_frames = await self.time_frames()
        assert all(time_frame in time_frames for time_frame in (
            TimeFrames.ONE_MINUTE.value,
            TimeFrames.THREE_MINUTES.value,
            TimeFrames.FIVE_MINUTES.value,
            TimeFrames.FIFTEEN_MINUTES.value,
            TimeFrames.THIRTY_MINUTES.value,
            TimeFrames.ONE_HOUR.value,
            TimeFrames.TWO_HOURS.value,
            TimeFrames.FOUR_HOURS.value,
            TimeFrames.SIX_HOURS.value,
            TimeFrames.TWELVE_HOURS.value,
            TimeFrames.ONE_DAY.value,
            TimeFrames.ONE_WEEK.value,
            TimeFrames.ONE_MONTH.value
        ))

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(2400, 2400)

    async def test_get_market_status(self):
        for market_status in await self.get_market_statuses():
            self.ensure_required_market_status_values(market_status)
            # on Bybit, precision is a decimal instead of a number of digits
            assert 0 < market_status[Ecmsc.PRECISION.value][
                Ecmsc.PRECISION_AMOUNT.value] <= 1  # to be fixed in Bybit tentacle
            assert 0 < market_status[Ecmsc.PRECISION.value][
                Ecmsc.PRECISION_PRICE.value] <= 1  # to be fixed in Bybit tentacle
            assert all(elem in market_status[Ecmsc.LIMITS.value]
                       for elem in (Ecmsc.LIMITS_AMOUNT.value,
                                    Ecmsc.LIMITS_PRICE.value,
                                    Ecmsc.LIMITS_COST.value))
            # min cost and price can be inferior or equal as we are in /USD futures
            self.check_market_status_limits(market_status,
                                            low_price_min=0.0001,    # XRP/USD
                                            low_price_max=0.1,    # XRP/USD
                                            expect_invalid_price_limit_values=False,
                                            expect_inferior_or_equal_price_and_cost=True)

    async def test_get_symbol_prices(self):
        # without limit
        symbol_prices = await self.get_symbol_prices()
        assert len(symbol_prices) == 200
        # max is 1000 on Bybit
        symbol_prices = await self.get_symbol_prices(limit=200)
        assert len(symbol_prices) == 200
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

        # fetching more than 200 candles is fetching candles from the past
        symbol_prices = await self.get_symbol_prices(limit=1500)
        assert len(symbol_prices) == 1000
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

        # try with candles limit (used in candled updater)
        symbol_prices = await self.get_symbol_prices(limit=200)
        assert len(symbol_prices) == 200
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

    async def test_get_historical_symbol_prices(self):
        # try with since and limit (used in data collector)
        for limit in (50, None):
            symbol_prices = await self.get_symbol_prices(since=self.CANDLE_SINCE, limit=limit)
            if limit:
                assert len(symbol_prices) == limit
            else:
                assert len(symbol_prices) > 5
            # check candles order (oldest first)
            self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
            # check that fetched candles are historical candles
            max_candle_time = self.get_time_after_time_frames(self.CANDLE_SINCE_SEC, len(symbol_prices))
            assert max_candle_time <= self.get_time()
            for candle in symbol_prices:
                assert self.CANDLE_SINCE_SEC <= candle[PriceIndexes.IND_PRICE_TIME.value] <= max_candle_time

    async def test_get_historical_ohlcv(self):
        await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        kline_price = await self.get_kline_price()
        assert len(kline_price) == 1
        assert len(kline_price[0]) == 6
        kline_start_time = kline_price[0][PriceIndexes.IND_PRICE_TIME.value]
        # assert kline is the current candle
        assert kline_start_time >= self.get_time() - self.get_allowed_time_delta()

    async def test_get_order_book(self):
        order_book = await self.get_order_book()
        assert 0 < order_book[Ecobic.TIMESTAMP.value] < self._get_ref_order_book_timestamp()
        assert len(order_book[Ecobic.ASKS.value]) == 5
        assert len(order_book[Ecobic.ASKS.value][0]) == 2
        assert len(order_book[Ecobic.BIDS.value]) == 5
        assert len(order_book[Ecobic.BIDS.value][0]) == 2
        
    async def test_get_order_books(self):
        # not supported
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        recent_trades = await self.get_recent_trades()
        assert len(recent_trades) == 50
        # check trades order (oldest first)
        self.ensure_elements_order(recent_trades, Ecoc.TIMESTAMP.value)

    async def test_get_price_ticker(self):
        ticker = await self.get_price_ticker()
        self._check_ticker(ticker, self.SYMBOL, check_content=True)

    async def test_get_all_currencies_price_ticker(self):
        tickers = await self.get_all_currencies_price_ticker()
        for symbol, ticker in tickers.items():
            self._check_ticker(ticker, symbol)

    async def test_get_funding_rate(self):
        funding_rate, ticker_funding_rate = await self.get_funding_rate()
        # patch LAST_FUNDING_TIME in tentacle
        self._check_funding_rate(funding_rate, has_last_time=False)
        # missing PREDICTED_FUNDING_RATE, find order info in info (exchange tentacle)
        self._check_funding_rate(ticker_funding_rate, has_rate=False, has_last_time=False,
                                 has_next_rate=False, has_next_time=False)
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

    @staticmethod
    def _check_ticker(ticker, symbol, check_content=False):
        assert ticker[Ectc.SYMBOL.value] == symbol
        assert all(key in ticker for key in (
            Ectc.HIGH.value,
            Ectc.LOW.value,
            Ectc.BID.value,
            Ectc.BID_VOLUME.value,
            Ectc.ASK.value,
            Ectc.ASK_VOLUME.value,
            Ectc.OPEN.value,
            Ectc.CLOSE.value,
            Ectc.LAST.value,
            Ectc.PREVIOUS_CLOSE.value
        ))
        if check_content:
            assert ticker[Ectc.HIGH.value]
            assert ticker[Ectc.LOW.value]
            assert ticker[Ectc.BID.value]
            assert ticker[Ectc.BID_VOLUME.value]
            assert ticker[Ectc.ASK.value]
            assert ticker[Ectc.ASK_VOLUME.value]
            assert ticker[Ectc.OPEN.value]
            assert ticker[Ectc.CLOSE.value]
            assert ticker[Ectc.LAST.value]
            assert ticker[Ectc.PREVIOUS_CLOSE.value] is None
            assert ticker[Ectc.BASE_VOLUME.value]
            assert ticker[Ectc.TIMESTAMP.value] is None  # will trigger an 'Ignored incomplete ticker'
            RealFuturesExchangeTester.check_ticker_typing(ticker, check_timestamp=False)
