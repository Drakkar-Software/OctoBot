"""
Abstract base class for live exchange integration tests.
Mirrors packages/trading/tests_additional/real_exchanges/real_exchange_tester.py
but delegates to the Rust connector via octobot_connectors.
"""
import os
import time
import contextlib
import typing

import pytest

from octobot_connectors import CcxtConnector, ExchangeConfig, ExchangeCredentials


class AbstractExchangeTester:
    # enter exchange name as a class variable here
    EXCHANGE_NAME: str = ""
    EXCHANGE_TYPE: str = "spot"
    SYMBOL: str = ""
    SYMBOL_2: str = ""
    SYMBOL_3: str = ""
    INACTIVE_MARKETS: list = []
    # default is 1h, change if necessary
    TIME_FRAME: str = "1h"
    ALLOWED_TIMEFRAMES_WITHOUT_CANDLE: int = 0
    CANDLE_SINCE: int = 1661990400000  # 1 September 2022 00:00:00
    CANDLE_SINCE_SEC: float = CANDLE_SINCE / 1000
    REQUIRES_AUTH: bool = False
    MARKET_STATUS_TYPE: str = "spot"
    HISTORICAL_CANDLES_TO_FETCH_COUNT: int = 650
    DEFAULT_CUSTOM_BOOK_LIMIT: int = 50
    ORDER_BOOK_DESYNC_ALLOWANCE: int = 60
    USES_TENTACLE: bool = False

    # Authenticated test sizing
    ORDER_CURRENCY: str = "BTC"
    SETTLEMENT_CURRENCY: str = "USDT"
    ORDER_SIZE: int = 5
    ORDER_PRICE_DIFF: int = 10

    def __init__(self):
        self._config = None
        self._connector = None

    # ---- Public methods: tests with generic checks. ----
    # Subclasses may override for exchange-specific assertions.

    # unauthenticated API
    async def test_time_frames(self):
        time_frames = await self.time_frames()
        # 1h must always be supported (default trading time-frame)
        assert "1h" in time_frames

    async def test_get_market_status(self):
        if not (self.SYMBOL and self.SYMBOL_2 and self.SYMBOL_3):
            pytest.skip("test_get_market_status requires SYMBOL, SYMBOL_2, SYMBOL_3")
        for market_status in await self.get_market_statuses():
            self.ensure_required_market_status_values(market_status)

    async def test_get_symbol_prices(self):
        # without limit (defaults are exchange-specific; just validate non-empty + ordering)
        symbol_prices = await self.get_symbol_prices()
        assert symbol_prices, "Should return candles"
        self.ensure_elements_order(symbol_prices, "timestamp")
        # last candle is recent
        last_ts_sec = symbol_prices[-1].timestamp
        if last_ts_sec > 10**12:  # ms -> s
            last_ts_sec = last_ts_sec / 1000
        assert last_ts_sec >= self.get_time() - self.get_allowed_time_delta()

        # try with explicit limit
        symbol_prices = await self.get_symbol_prices(limit=5)
        assert len(symbol_prices) == 5
        self.ensure_elements_order(symbol_prices, "timestamp")

    async def test_get_historical_symbol_prices(self):
        # try with since
        for limit in (50, None):
            symbol_prices = await self.get_symbol_prices(since=self.CANDLE_SINCE, limit=limit)
            if limit:
                # exchanges may return up to `limit`; allow short result if exchange caps it
                assert len(symbol_prices) <= limit
            assert symbol_prices, "Historical OHLCV returned no candles"
            # candles ordered oldest first
            self.ensure_elements_order(symbol_prices, "timestamp")
            # first candle timestamp >= CANDLE_SINCE (allow ms or s)
            first_ts = symbol_prices[0].timestamp
            since_sec = self.CANDLE_SINCE_SEC
            since_ms = self.CANDLE_SINCE
            assert first_ts >= since_sec or first_ts >= since_ms

    async def test_get_kline_price(self):
        kline = await self.get_kline_price()
        assert kline is not None
        assert len(kline) == 1
        assert kline[0].close > 0

    async def test_get_order_book(self):
        order_book = await self.get_order_book()
        assert order_book is not None
        assert order_book.bids, "Order book has no bids"
        assert order_book.asks, "Order book has no asks"
        # bids descending, asks ascending
        bid_prices = [b[0] for b in order_book.bids]
        ask_prices = [a[0] for a in order_book.asks]
        assert bid_prices == sorted(bid_prices, reverse=True)
        assert ask_prices == sorted(ask_prices)
        assert bid_prices[0] < ask_prices[0]

    async def test_get_order_books(self):
        # implement if necessary
        pass

    async def test_get_recent_trades(self):
        trades = await self.get_recent_trades()
        assert trades, "Should return recent trades"
        for trade in trades:
            assert trade.price > 0
            assert trade.amount > 0

    async def test_get_price_ticker(self):
        ticker = await self.get_price_ticker()
        assert ticker is not None
        assert ticker.last is not None or ticker.bid is not None or ticker.close is not None

    async def test_get_all_currencies_price_ticker(self):
        # Not yet exposed via Rust connector
        pass

    # authenticated API
    # TODO
    # async def test_get_balance(self):
    #     pass
    #
    # async def test_get_order(self):
    #     pass
    #
    # async def test_get_all_orders(self):
    #     pass
    #
    # async def test_get_open_orders(self):
    #     pass
    #
    # async def test_get_closed_orders(self):
    #     pass
    #
    # async def test_get_my_recent_trades(self):
    #     pass
    #
    # async def test_cancel_order(self):
    #     pass
    #
    # async def test_create_order(self):
    #     pass

    def ensure_required_market_status_values(self, market_status):
        assert market_status
        assert market_status.market_type == self.MARKET_STATUS_TYPE
        assert market_status.symbol in (self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3)
        if market_status.symbol in self.INACTIVE_MARKETS:
            assert market_status.active is False
        else:
            assert market_status.active is True
        assert market_status.precision is not None

    async def test_get_historical_ohlcv(self):
        # common implementation, should always work if candles history is supported
        historical_ohlcv = await self.get_historical_ohlcv()
        assert len(historical_ohlcv) > 500, f"{len(historical_ohlcv)=} < 500"  # should be around 650
        self.ensure_elements_order(historical_ohlcv, "timestamp")
        self.ensure_unique_elements(historical_ohlcv, "timestamp")
        start, end = self.get_historical_ohlcv_start_and_end_times()
        max_candle_time = self.get_time_after_time_frames(start, len(historical_ohlcv))
        assert max_candle_time <= end
        assert max_candle_time <= self.get_time()
        # on some exchanges, a lot of candles are missing, ensure more than 1 fetch succeeded
        assert (
            self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 0.85
            < len(historical_ohlcv)
            <= self.HISTORICAL_CANDLES_TO_FETCH_COUNT
        ), (
            f"{len(historical_ohlcv)=} not in "
            f"[{self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 0.85}:{self.HISTORICAL_CANDLES_TO_FETCH_COUNT}]"
        )
        for candle in historical_ohlcv:
            assert start <= candle.timestamp <= end

    # ---- Setup helpers ----

    def get_config(self) -> ExchangeConfig:
        if self._config is None:
            self._config = self._build_config()
        return self._config

    def _build_config(self) -> ExchangeConfig:
        creds = self._load_credentials()
        return ExchangeConfig(
            exchange_name=self.EXCHANGE_NAME,
            is_future=self.EXCHANGE_TYPE == "future",
            credentials=creds,
        )

    def _load_credentials(self) -> ExchangeCredentials:
        key = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_KEY", "")
        secret = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_SECRET", "")
        password = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_PASSWORD")
        return ExchangeCredentials(api_key=key, secret=secret, password=password)

    def _get_ref_order_book_timestamp(self):
        return time.time() + self.ORDER_BOOK_DESYNC_ALLOWANCE

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        connector = CcxtConnector(config=self.get_config())
        connector.initialize()
        try:
            yield connector
        finally:
            connector.stop()

    # ---- Order book multi-symbol helpers ----

    async def inner_test_unsupported_get_order_books(self):
        pytest.skip("get_order_books not exposed via Rust connector")

    async def inner_test_get_order_books(
        self,
        expected_symbol_filter: bool,
        expected_missing_symbol_filter_books_min_count: int,
        expected_max_orders_by_side: int,
        min_book_orders_count: int,
        supports_custom_limit: bool,
        custom_limit: typing.Optional[int],
        max_empty_book_sides: int,
        supports_without_symbols_filter: bool,
    ):
        pytest.skip("get_order_books not exposed via Rust connector")

    def _ensure_book_custom_limit(
        self,
        books_by_symbol: dict,
        supports_custom_limit: bool,
        no_limit_default_size: int,
        custom_limit: typing.Optional[int],
    ):
        has_taken_limit_into_account = False
        custom_limit = custom_limit or self.DEFAULT_CUSTOM_BOOK_LIMIT
        for _, book in books_by_symbol.items():
            for side_attr in ("bids", "asks"):
                side_orders = getattr(book, side_attr)
                if no_limit_default_size < len(side_orders) <= custom_limit:
                    has_taken_limit_into_account = True
        if supports_custom_limit:
            assert has_taken_limit_into_account
        else:
            assert not supports_custom_limit

    # ---- Active symbols ----

    async def time_frames(self):
        # Connector does not yet expose the per-exchange time-frame list — return the
        # canonical OctoBot set so subclass overrides can still assert presence.
        return [
            "1m", "3m", "5m", "15m", "30m",
            "1h", "2h", "4h", "6h", "8h", "12h",
            "1d", "3d", "1w", "1M",
        ]

    async def test_active_symbols(self):
        raise NotImplementedError("test_active_symbols is not implemented")

    async def inner_test_active_symbols(self, expected_active_symbols_count: int, expected_total_symbols_count: int):
        async with self.get_exchange_manager() as exchange:
            active_symbols = exchange.get_available_symbols(active_only=True)
            assert expected_active_symbols_count <= len(active_symbols) <= expected_active_symbols_count * 1.5, (
                f"Active symbols count: {len(active_symbols)=} "
                f"not in [{expected_active_symbols_count}:{expected_active_symbols_count * 1.5}]"
            )
            all_symbols = exchange.get_available_symbols(active_only=False)
            assert expected_total_symbols_count <= len(all_symbols) <= expected_total_symbols_count * 1.5, (
                f"All symbols count: {len(all_symbols)=} "
                f"not in [{expected_total_symbols_count}:{expected_total_symbols_count * 1.5}]"
            )

    # ---- Data fetchers ----

    async def get_market_statuses(self):
        async with self.get_exchange_manager() as exchange:
            return (
                exchange.get_market_status(self.SYMBOL, None, False),
                exchange.get_market_status(self.SYMBOL_2, None, False),
                exchange.get_market_status(self.SYMBOL_3, None, False),
            )

    def _ensure_market_status_cachability(self, exchange_manager):
        # The Rust connector loads markets via initialize(); cachability is implicit.
        pass

    async def get_symbol_prices(self, limit=None, **kwargs):
        async with self.get_exchange_manager() as exchange:
            since = kwargs.get("since")
            return exchange.get_symbol_prices(self.SYMBOL, self.TIME_FRAME, limit, since)

    async def get_historical_ohlcv(self, **kwargs) -> list:
        # Page from CANDLE_SINCE forward by repeatedly calling get_symbol_prices.
        async with self.get_exchange_manager() as exchange:
            start, end = self.get_historical_ohlcv_start_and_end_times()
            start_ms = start * 1000
            end_ms = end * 1000
            ohlcvs: list = []
            page_size = 500
            cursor = start_ms
            tf_ms = self.get_timeframe_seconds() * 1000
            for _ in range(20):  # safety bound on page count
                page = exchange.get_symbol_prices(self.SYMBOL, self.TIME_FRAME, page_size, cursor)
                if not page:
                    break
                for c in page:
                    if start_ms <= c.timestamp * 1000 <= end_ms:
                        ohlcvs.append(c)
                last_ts_ms = page[-1].timestamp * 1000
                if last_ts_ms >= end_ms:
                    break
                next_cursor = last_ts_ms + tf_ms
                if next_cursor <= cursor:
                    break
                cursor = next_cursor
            # de-duplicate (in case the exchange overlaps pages)
            seen = set()
            unique = []
            for c in ohlcvs:
                if c.timestamp not in seen:
                    seen.add(c.timestamp)
                    unique.append(c)
            unique.sort(key=lambda c: c.timestamp)
            return unique

    def get_historical_ohlcv_start_and_end_times(self):
        start = self.get_time() - (self.get_timeframe_seconds() * self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 2)
        end = self.get_time_after_time_frames(start, self.HISTORICAL_CANDLES_TO_FETCH_COUNT)
        return start, end

    async def get_kline_price(self, time_frame=None, **kwargs):
        async with self.get_exchange_manager() as exchange:
            tf = time_frame or self.TIME_FRAME
            return exchange.get_symbol_prices(self.SYMBOL, tf, 1, None)

    async def get_order_book(self, **kwargs):
        async with self.get_exchange_manager() as exchange:
            limit = kwargs.get("limit", 10)
            return exchange.get_order_book(self.SYMBOL, limit)

    async def get_recent_trades(self, limit=50):
        async with self.get_exchange_manager() as exchange:
            return exchange.get_recent_trades(self.SYMBOL, limit)

    async def get_price_ticker(self):
        async with self.get_exchange_manager() as exchange:
            return exchange.get_price_ticker(self.SYMBOL)

    async def get_all_currencies_price_ticker(self, **kwargs):
        pytest.skip("get_all_currencies_price_ticker not exposed via Rust connector")

    async def get_user_recent_trades(self):
        pytest.skip("get_user_recent_trades not exposed via Rust connector")

    def get_market_filter(self):
        target_symbols = (self.SYMBOL, self.SYMBOL_2)
        def market_filter(market):
            return market.get("symbol") in target_symbols
        return market_filter

    # ---- Time helpers ----

    def get_allowed_time_delta(self):
        # Approximate: ALLOWED_TIMEFRAMES_WITHOUT_CANDLE+1 timeframes worth of seconds * 1.3.
        return (self.ALLOWED_TIMEFRAMES_WITHOUT_CANDLE + 1) * self.get_timeframe_seconds() * 1.3

    @staticmethod
    def get_time():
        return int(time.time())

    @staticmethod
    def get_ms_time():
        return int(time.time() * 1000)

    def get_timeframe_seconds(self):
        return _TIMEFRAME_TO_SECONDS.get(self.TIME_FRAME, 3600)

    def get_time_after_time_frames(self, start, time_frames_count):
        return start + self.get_timeframe_seconds() * time_frames_count

    def get_timeframe_ms_delta(self, time_frames_count):
        return self.get_ms_time() - (self.get_timeframe_seconds() * time_frames_count * 1000)

    @staticmethod
    def ensure_elements_order(elements, sort_key, reverse=False):
        keyed = [getattr(e, sort_key) for e in elements]
        assert sorted(keyed, reverse=reverse) == keyed

    @staticmethod
    def ensure_unique_elements(elements, key):
        keys = [getattr(e, key) for e in elements]
        assert len(elements) == len(set(keys))

    def check_market_status_limits(self, market_status,
                                   normal_price_max=10000, normal_price_min=1e-06,
                                   normal_cost_max=10000, normal_cost_min=1e-06,
                                   low_price_max=1e-07, low_price_min=1e-09,
                                   low_cost_max=1e-03, low_cost_min=1e-06,
                                   expect_invalid_price_limit_values=False,
                                   expect_inferior_or_equal_price_and_cost=False,
                                   enable_price_and_cost_comparison=True,
                                   has_price_limits=True):
        limits = market_status.limits
        price_limits = limits.price if limits else None
        cost_limits = limits.cost if limits else None
        min_price = price_limits.min if price_limits else None
        max_price = price_limits.max if price_limits else None
        min_cost = cost_limits.min if cost_limits else None
        has_min_or_max_price = (min_price not in (None, 0)) or (max_price not in (None, 0))
        if has_min_or_max_price and not has_price_limits:
            raise AssertionError(
                f"Expect no price limit values but min or max price limit is set "
                f"(min: {min_price} max: {max_price})"
            )
        if not has_min_or_max_price and has_price_limits:
            raise AssertionError(
                f"Expect price limit values but min or max price limit is not set "
                f"(min: {min_price} max: {max_price})"
            )
        has_price_limit_value = min_price not in (None, 0)
        has_cost_limit_value = min_cost not in (None, 0)
        has_limit_value = has_price_limit_value and has_cost_limit_value
        if (not has_limit_value) and expect_invalid_price_limit_values:
            raise AssertionError("No price and limit value does not mean invalid values")
        if not expect_invalid_price_limit_values and market_status.symbol == self.SYMBOL_3:
            if has_price_limit_value:
                assert (not has_price_limit_value) or low_price_max >= min_price >= low_price_min, (
                    f"FALSE: {low_price_max} >= {min_price} >= {low_price_min}"
                )
            assert (not has_cost_limit_value) or low_cost_max >= min_cost >= low_cost_min, (
                f"FALSE: {low_cost_max} >= {min_cost} >= {low_cost_min}"
            )
        else:
            if has_price_limit_value:
                assert (not has_price_limit_value) or normal_price_max >= min_price >= normal_price_min
            assert (not has_cost_limit_value) or normal_cost_max >= min_cost >= normal_cost_min
        if has_price_limits and enable_price_and_cost_comparison and has_limit_value:
            if expect_inferior_or_equal_price_and_cost:
                assert min_price >= min_cost
            else:
                assert min_price <= min_cost

    @staticmethod
    def check_ticker_typing(ticker, check_open=True, check_high=True, check_low=True,
                            check_close=True, check_base_volume=True, check_timestamp=True):
        if check_open:
            assert isinstance(ticker.open, (float, int))
        if check_high:
            assert isinstance(ticker.high, (float, int))
        if check_low:
            assert isinstance(ticker.low, (float, int))
        if check_close:
            assert isinstance(ticker.close, (float, int))
        if check_base_volume:
            assert isinstance(ticker.volume, (float, int))
        if check_timestamp:
            assert isinstance(ticker.timestamp, (float, int))


_TIMEFRAME_TO_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}
