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

from octobot_commons.enums import TimeFrames, PriceIndexes
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsOrderBookInfoColumns as Ecobic, ExchangeConstantsOrderColumns as Ecoc, \
    ExchangeConstantsTickersColumns as Ectc
from tests_additional.real_exchanges.real_exchange_tester import RealExchangeTester
# required to catch async loop context exceptions
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBingxRealExchangeTester(RealExchangeTester):
    EXCHANGE_NAME = "bingx"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "SHIB/USDT"
    CANDLE_SINCE = 1729505232000  # Sunday, August 18, 2024 6:20:32 PM GMT (large differences not supported)
    CANDLE_SINCE_SEC = CANDLE_SINCE / 1000

    async def _test_time_frames(self):
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
            TimeFrames.THREE_DAYS.value,
            TimeFrames.ONE_WEEK.value,
            TimeFrames.ONE_MONTH.value
        ))

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(1300, 1900)

    async def test_get_market_status(self):
        for market_status in await self.get_market_statuses():
            # on Bingx, precision is a decimal instead of a number of digits
            if market_status[Ecmsc.SYMBOL.value] == self.SYMBOL_3:
                assert 0 < market_status[Ecmsc.PRECISION.value][
                    Ecmsc.PRECISION_AMOUNT.value] <= 1  # to be fixed in Bingx tentacle
            else:
                assert 0 < market_status[Ecmsc.PRECISION.value][
                    Ecmsc.PRECISION_AMOUNT.value] < 1  # to be fixed in Bingx tentacle
            assert 0 < market_status[Ecmsc.PRECISION.value][
                Ecmsc.PRECISION_PRICE.value] < 1  # to be fixed in Bingx tentacle
            assert all(elem in market_status[Ecmsc.LIMITS.value]
                       for elem in (Ecmsc.LIMITS_AMOUNT.value,
                                    Ecmsc.LIMITS_PRICE.value,
                                    Ecmsc.LIMITS_COST.value))
            self.check_market_status_limits(
                market_status,
                has_price_limits=False,
                low_cost_max=5 if market_status[Ecmsc.SYMBOL.value] == self.SYMBOL_3 else 1e-03,
                expect_invalid_price_limit_values=False
            )

    async def test_get_symbol_prices(self):
        # without limit
        symbol_prices = await self.get_symbol_prices()
        assert len(symbol_prices) == 500
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

        # try with candles limit (used in candled updater)
        symbol_prices = await self.get_symbol_prices(limit=1500)
        # max candles is 1000
        assert len(symbol_prices) == 1000
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

    async def test_get_historical_symbol_prices(self):
        # try with since and limit (used in data collector)
        # try with since and no limit (used in get_historical_ohlcv)

        for since_value in (
            self.CANDLE_SINCE,
            super().CANDLE_SINCE,
        ):
            candle_since_sec = since_value / 1000
            for limit in (None, None):
                symbol_prices = await self.get_symbol_prices(since=since_value, limit=limit)
                if limit:
                    assert len(symbol_prices) == limit
                else:
                    assert len(symbol_prices) > 5
                # check candles order (oldest first)
                self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
                # check that fetched candles are historical candles
                max_candle_time = self.get_time_after_time_frames(candle_since_sec, len(symbol_prices))
                assert max_candle_time <= self.get_time()
                for candle in symbol_prices:
                    if since_value == super().CANDLE_SINCE:
                        assert candle_since_sec <= candle[PriceIndexes.IND_PRICE_TIME.value]
                        # ensure that still can't fetch candle before self.CANDLE_SINCE
                        # this fails if fetch works
                        assert max_candle_time < candle[PriceIndexes.IND_PRICE_TIME.value]
                        max_theoretical_bingx_candle_time = self.get_time_after_time_frames(
                            self.CANDLE_SINCE_SEC, len(symbol_prices)
                        )
                        # ensure fetch data are just moved to the 1st available candles but are still making sense
                        assert (
                            super().CANDLE_SINCE_SEC
                            <= candle[PriceIndexes.IND_PRICE_TIME.value]
                            <= max_theoretical_bingx_candle_time
                        )
                    else:
                        # when fetching after january 2023, it works
                        assert candle_since_sec <= candle[PriceIndexes.IND_PRICE_TIME.value] <= max_candle_time

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
            assert ticker[Ectc.TIMESTAMP.value]
            RealExchangeTester.check_ticker_typing(ticker)
