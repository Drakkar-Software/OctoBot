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
import contextlib

import pytest
import unittest.mock as mock

import octobot_commons.enums as common_enums
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsOrderBookInfoColumns as Ecobic, ExchangeConstantsOrderColumns as Ecoc, \
    ExchangeConstantsTickersColumns as Ectc
from tests_additional.real_exchanges.real_exchange_tester import RealExchangeTester
from tests_additional.real_exchanges.real_option_exchange_tester import RealOptionExchangeTester
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums

# required to catch async loop context exceptions
from tests import event_loop

try:
    from tentacles.Trading.Exchange.polymarket.ccxt.polymarket_async import polymarket
except ImportError:
    # test will be skipped if the tentacle is not installed
    pytest.skip(
        "Polymarket tentacle is not installed, skipping TestPolymarketRealExchangeTester",
        allow_module_level=True
    )

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

# Fetching Polymarket's 70k+ markets is slow (~10s). After the first load_markets() call, cache
# all already-processed market attributes. Subsequent get_exchange_manager() calls inject them as
# direct reference assignments — same as ccxt's set_markets_from_exchange — bypassing both the
# network fetch and the expensive set_markets() re-indexing of 70k objects.
_markets_cache: dict | None = None


class TestPolymarketRealExchangeTester(RealOptionExchangeTester):
    EXCHANGE_NAME = "polymarket"
    SYMBOL = f"will-bitcoin-replace-sha-256-before-2027/USDC:USDC-261231-0-YES"
    SYMBOL_2 = f"will-the-us-confirm-that-aliens-exist-before-2027/USDC:USDC-261231-0-YES"
    SYMBOL_3 = f"10pt0-or-above-earthquake-before-2027/USDC:USDC-261231-0-YES"
    TIME_FRAME = common_enums.TimeFrames.ONE_MINUTE
    USES_TENTACLE = True  # set True when an exchange tentacles should be used in this test
    PROFILE_ID = "0x16b29c50f2439faf627209b2ac0c7bbddaa8a881" # https://polymarket.com/@SeriouslySirius
    ALLOWED_TIMEFRAMES_WITHOUT_CANDLE = 3  # Polymarket 1m candles can lag; allow up to 4 candles of delta

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        global _markets_cache
        if _markets_cache is None:
            async with super().get_exchange_manager(market_filter) as exchange_manager:
                client = exchange_manager.exchange.connector.client
                _markets_cache = {
                    "markets": client.markets,
                    "markets_by_id": client.markets_by_id,
                    "symbols": client.symbols,
                    "ids": client.ids,
                    "currencies": client.currencies,
                    "currencies_by_id": client.currencies_by_id,
                    "baseCurrencies": client.baseCurrencies,
                    "quoteCurrencies": client.quoteCurrencies,
                    "codes": client.codes,
                }
                yield exchange_manager
        else:
            cached = _markets_cache

            async def _load_from_cache(self_ccxt, reload=False, params={}):
                self_ccxt.markets = cached["markets"]
                self_ccxt.markets_by_id = cached["markets_by_id"]
                self_ccxt.symbols = cached["symbols"]
                self_ccxt.ids = cached["ids"]
                self_ccxt.currencies = cached["currencies"]
                self_ccxt.currencies_by_id = cached["currencies_by_id"]
                self_ccxt.baseCurrencies = cached["baseCurrencies"]
                self_ccxt.quoteCurrencies = cached["quoteCurrencies"]
                self_ccxt.codes = cached["codes"]
                return self_ccxt.markets

            with mock.patch.object(polymarket, "load_markets", _load_from_cache):
                async with super().get_exchange_manager(market_filter) as exchange_manager:
                    yield exchange_manager

    async def test_time_frames(self):
        time_frames = await self.time_frames()
        assert all(time_frame in time_frames for time_frame in (
            common_enums.TimeFrames.ONE_MINUTE.value,
            common_enums.TimeFrames.ONE_HOUR.value,
            common_enums.TimeFrames.SIX_HOURS.value,
            common_enums.TimeFrames.ONE_DAY.value,
            common_enums.TimeFrames.ONE_WEEK.value,
        ))

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(50000, 60000)

    def _ensure_market_status_cachability(self, exchange_manager):
        # Polymarket loads ~70k+ markets; the market cache deepcopy is too large to validate in tests.
        # Skip the cache-round-trip check and only verify the live exchange markets are accessible.
        pass

    async def test_get_market_status(self):
        # Debug code to print the symbol of the slugs
        # slugs = ['10pt0-or-above-earthquake-before-2027', 'will-bitcoin-replace-sha-256-before-2027', 'will-the-us-confirm-that-aliens-exist-before-2027']
        # async with self.get_exchange_manager() as exchange_manager:
        #     for market in exchange_manager.exchange.connector.client.markets:
        #         for slug in slugs:
        #             if market.startswith(slug):
        #                 print(exchange_manager.exchange.connector.client.markets[market])
        for market_status in await self.get_market_statuses():
            self.ensure_required_market_status_values(market_status)
            # Polymarket options are probabilities (0-1 USDC); SYMBOL_3 is a near-zero probability
            # event so its min_price (~1e-06) is higher than the default low_price_max (1e-07).
            self.check_market_status_limits(
                market_status, has_price_limits=True, low_price_max=1e-05, low_price_min=1e-08
            )

    async def test_get_symbol_prices(self):
        # without limit
        symbol_prices = await self.get_symbol_prices()
        assert len(symbol_prices) >= 1000
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, common_enums.PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

        # try with candles limit (used in candled updater)
        symbol_prices = await self.get_symbol_prices(limit=200)
        assert len(symbol_prices) == 200
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, common_enums.PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

    async def test_get_historical_symbol_prices(self):
        # try with since and limit (used in data collector)
        for limit in (50, None):
            symbol_prices = await self.get_symbol_prices(since=self.CANDLE_SINCE, limit=limit)
            if limit:
                assert len(symbol_prices) == limit
            else:
                assert len(symbol_prices) > 5
            # check candles order (oldest first)
            self.ensure_elements_order(symbol_prices, common_enums.PriceIndexes.IND_PRICE_TIME.value)
            # check that fetched candles are historical candles
            max_candle_time = self.get_time_after_time_frames(self.CANDLE_SINCE_SEC, len(symbol_prices))
            assert max_candle_time <= self.get_time()
            with pytest.raises(AssertionError):  # not supported
                for candle in symbol_prices:
                    assert self.CANDLE_SINCE_SEC <= candle[common_enums.PriceIndexes.IND_PRICE_TIME.value] <= max_candle_time

    async def test_get_historical_ohlcv(self):
        # Polymarket does not honour the `since` parameter: candles are returned from the
        # beginning of the market regardless of the requested start time, so the standard
        # time-range and exact-count assertions from the base class do not apply here.
        historical_ohlcv = await self.get_historical_ohlcv()
        assert len(historical_ohlcv) > 500, f"{len(historical_ohlcv)=} < 500"
        self.ensure_elements_order(historical_ohlcv, common_enums.PriceIndexes.IND_PRICE_TIME.value)
        self.ensure_unique_elements(historical_ohlcv, common_enums.PriceIndexes.IND_PRICE_TIME.value)

    async def test_get_kline_price(self):
        kline_price = await self.get_kline_price()
        assert len(kline_price) == 1
        assert len(kline_price[0]) == 6
        kline_start_time = kline_price[0][common_enums.PriceIndexes.IND_PRICE_TIME.value]
        # assert kline is the current candle
        assert kline_start_time >= self.get_time() - self.get_allowed_time_delta()

    async def test_get_order_book(self):
        order_book = await self.get_order_book()
        assert 0 < order_book[Ecobic.TIMESTAMP.value] < self._get_ref_order_book_timestamp()
        assert len(order_book[Ecobic.ASKS.value]) >= 5
        assert len(order_book[Ecobic.ASKS.value][0]) == 2
        assert len(order_book[Ecobic.BIDS.value]) >= 5
        assert len(order_book[Ecobic.BIDS.value][0]) == 2
        
    async def test_get_order_books(self):
        await self.inner_test_get_order_books(
            True,
            1000, # asked symbols
            100, # up to 100 orders
            0, # from 0 orders
            False,
            None,
            0,
            False
        )

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
            assert ticker[Ectc.HIGH.value] is None
            assert ticker[Ectc.LOW.value] is None
            assert ticker[Ectc.BID.value]
            assert ticker[Ectc.BID_VOLUME.value] is None
            assert ticker[Ectc.ASK.value]
            assert ticker[Ectc.ASK_VOLUME.value] is None
            assert ticker[Ectc.OPEN.value] is None
            assert ticker[Ectc.CLOSE.value]
            assert ticker[Ectc.LAST.value]
            assert ticker[Ectc.PREVIOUS_CLOSE.value] is None
            assert ticker[Ectc.BASE_VOLUME.value] is not None
            assert ticker[Ectc.TIMESTAMP.value]
            RealExchangeTester.check_ticker_typing(
                ticker, 
                check_open=False, 
                check_high=False, 
                check_low=False, 
                check_close=True,
                check_base_volume=True, 
                check_timestamp=True
            )

    async def test_fetch_user_positions(self, **kwargs):
        positions = await self.get_user_positions(**kwargs)
        for position in positions:
            self._check_position(position)

    async def test_fetch_user_closed_positions(self, **kwargs):
        # positions = await self.get_user_closed_positions(**kwargs)
        # for position in positions:
        #     self._check_position(position, is_closed=True)
        pass # Not possible while market statuses cannot be dynamically updated

    def _check_position(self, position, check_symbol=False, is_closed=False):
        assert position
        if check_symbol:
            assert position[ccxt_enums.ExchangePositionCCXTColumns.SYMBOL.value] == self.SYMBOL
        else:
            assert position[ccxt_enums.ExchangePositionCCXTColumns.SYMBOL.value] is not None
        assert position[ccxt_enums.ExchangePositionCCXTColumns.ENTRY_PRICE.value] > 0
        if is_closed:
            assert position[ccxt_enums.ExchangePositionCCXTColumns.TIMESTAMP.value] > 0
        else:
            assert position[ccxt_enums.ExchangePositionCCXTColumns.MARK_PRICE.value] is not None # can be 0.0 on Polymarket
            assert position[ccxt_enums.ExchangePositionCCXTColumns.UNREALISED_PNL.value] is not None
            assert position[ccxt_enums.ExchangePositionCCXTColumns.COLLATERAL.value] >= 0
            assert position[ccxt_enums.ExchangePositionCCXTColumns.NOTIONAL.value] is not None # can be 0.0
            assert position[ccxt_enums.ExchangePositionCCXTColumns.SIDE.value] is not None
        assert position[ccxt_enums.ExchangePositionCCXTColumns.REALISED_PNL.value] is not None # can be 0.0
        assert ccxt_enums.ExchangePositionCCXTColumns.CONTRACT_SIZE.value in position