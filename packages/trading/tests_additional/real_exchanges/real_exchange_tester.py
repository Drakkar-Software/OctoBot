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
import dataclasses
import decimal
import enum
import time
from types import NoneType
import typing

import pytest
from ccxt import Exchange
import ccxt
import octobot_commons.constants as constants
import octobot_commons.enums as commons_enums
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.util as exchanges_util
from octobot_trading.enums import ExchangeConstantsTickersColumns as Ectc, \
    ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsDexPairsColumns as Ecdpc
from tests_additional.real_exchanges import get_exchange_manager


class TickerExpect(enum.Enum):
    TRUTHY = "truthy"
    NONE = "none"
    NOT_NONE = "not_none"
    SKIP = "skip"


@dataclasses.dataclass
class TickerRequiredExpectations:
    high: TickerExpect | None = None
    low: TickerExpect | None = None
    bid: TickerExpect | None = None
    bid_volume: TickerExpect | None = None
    ask: TickerExpect | None = None
    ask_volume: TickerExpect | None = None
    open: TickerExpect | None = None
    close: TickerExpect | None = None
    last: TickerExpect | None = None
    previous_close: TickerExpect | None = None
    base_volume: TickerExpect | None = None
    quote_volume: TickerExpect | None = None
    timestamp: TickerExpect | None = None


_TICKER_EXPECT_ATTR_TO_COLUMN: dict[str, str] = {
    "high": Ectc.HIGH.value,
    "low": Ectc.LOW.value,
    "bid": Ectc.BID.value,
    "bid_volume": Ectc.BID_VOLUME.value,
    "ask": Ectc.ASK.value,
    "ask_volume": Ectc.ASK_VOLUME.value,
    "open": Ectc.OPEN.value,
    "close": Ectc.CLOSE.value,
    "last": Ectc.LAST.value,
    "previous_close": Ectc.PREVIOUS_CLOSE.value,
    "base_volume": Ectc.BASE_VOLUME.value,
    "quote_volume": Ectc.QUOTE_VOLUME.value,
    "timestamp": Ectc.TIMESTAMP.value,
}


def _default_ticker_content_expectations() -> dict[str, TickerExpect]:
    return {
        Ectc.HIGH.value: TickerExpect.TRUTHY,
        Ectc.LOW.value: TickerExpect.TRUTHY,
        Ectc.BID.value: TickerExpect.TRUTHY,
        Ectc.BID_VOLUME.value: TickerExpect.NONE,
        Ectc.ASK.value: TickerExpect.TRUTHY,
        Ectc.ASK_VOLUME.value: TickerExpect.NONE,
        Ectc.OPEN.value: TickerExpect.TRUTHY,
        Ectc.CLOSE.value: TickerExpect.TRUTHY,
        Ectc.LAST.value: TickerExpect.TRUTHY,
        Ectc.PREVIOUS_CLOSE.value: TickerExpect.NONE,
        Ectc.BASE_VOLUME.value: TickerExpect.TRUTHY,
        Ectc.TIMESTAMP.value: TickerExpect.TRUTHY,
        Ectc.QUOTE_VOLUME.value: TickerExpect.SKIP,
    }


def _merge_ticker_content_expectations(
    expectations: typing.Optional[TickerRequiredExpectations],
    no_volume_in_ticker: bool = False,
) -> dict[str, TickerExpect]:
    merged = _default_ticker_content_expectations()
    if expectations is not None:
        for field in dataclasses.fields(TickerRequiredExpectations):
            override = getattr(expectations, field.name)
            if override is not None:
                column = _TICKER_EXPECT_ATTR_TO_COLUMN[field.name]
                merged[column] = override
    if no_volume_in_ticker:
        merged[Ectc.BASE_VOLUME.value] = TickerExpect.NONE
        merged[Ectc.QUOTE_VOLUME.value] = TickerExpect.NONE
    return merged


def _market_precision_decimal_places_or_tick(value: typing.Any) -> None:
    """
    CCXT precision can be decimal-place counts (>=1, int or 8.0-style float) or positive
    fractional tick sizes; None is left to the caller.
    Several exchanges/CCXT configs use ``0`` for 'unspecified'; treat like None here.
    """
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, decimal.Decimal) and value == 0:
        return
    if isinstance(value, (int, float)) and value == 0:
        return
    if isinstance(value, decimal.Decimal):
        normalized = decimal.Decimal(str(value)).normalize()
        if normalized <= 0:
            raise AssertionError(f"market precision/tick must be positive, got {value!r}")
        if normalized != normalized.to_integral():
            return
        if normalized < 1:
            raise AssertionError(
                "decimal-place precision counts should be >= 1 "
                f"(got {value!r}; tick sizes use non-integral decimals)"
            )
        return
    if isinstance(value, (int, float)):
        num = float(value)
        if num <= 0:
            raise AssertionError(f"market precision/tick must be positive, got {value!r}")
        if isinstance(value, float) and not value.is_integer():
            return
        if num < 1:
            raise AssertionError(
                "decimal-place precision counts should be >= 1 "
                f"(got {value!r}; tick sizes use positive non-integral floats)"
            )
        return
    raise AssertionError(f"unexpected precision/tick type: {type(value).__name__} {value!r}")


ORDER_TYPES_WITH_STOP_LOSS = [
    trading_enums.TradeOrderType.MARKET,
    trading_enums.TradeOrderType.LIMIT,
    trading_enums.TradeOrderType.STOP_LOSS,
]


class RealExchangeTester:
    # enter exchange name as a class variable here
    EXCHANGE_NAME = None
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.SPOT.value
    SYMBOL = None
    SYMBOL_2 = None
    SYMBOL_3 = None
    INACTIVE_MARKETS = []
    # default is 1h, change if necessary
    TIME_FRAME = commons_enums.TimeFrames.ONE_HOUR
    ALLOWED_TIMEFRAMES_WITHOUT_CANDLE = 0
    CANDLE_SINCE = 1661990400000  # 1 September 2022 00:00:00
    CANDLE_SINCE_SEC = CANDLE_SINCE / 1000
    REQUIRES_AUTH = False  # set True when even normally public apis require authentication
    MARKET_STATUS_TYPE = trading_enums.ExchangeTypes.SPOT.value
    HISTORICAL_CANDLES_TO_FETCH_COUNT = 650
    DEFAULT_CUSTOM_BOOK_LIMIT = 50
    ORDER_BOOK_DESYNC_ALLOWANCE = 60    # allow 60s desync
    USES_TENTACLE = False  # set True when an exchange tentacles should be used in this test
    MIN_TICKERS_TIMESTAMP_ALLOWANCE = 1704067200 # 1 January 2024 00:00:00

    # Public methods: to be implemented as tests
    # Use await self._[method_name] to get the test request result
    # ex: market_status = await self.get_market_status()

    # unauthenticated API
    async def test_time_frames(self):
        pass

    async def test_supports_order_type(self):
        pass

    async def test_get_market_status(self):
        pass

    async def test_get_symbol_prices(self):
        pass

    async def test_get_historical_symbol_prices(self):
        pass

    async def test_get_kline_price(self):
        pass

    async def test_get_order_book(self):
        pass

    async def test_get_order_books(self):
        # implement if necessary
        pass

    async def test_get_recent_trades(self):
        pass

    async def test_get_price_ticker(self):
        pass

    async def test_get_all_currencies_price_ticker(self):
        pass

    def ensure_required_market_status_values(self, market_status, expected_symbols=None):
        assert market_status, f"market_status must be a non-empty dict from the exchange, got {market_status!r}"
        if Ecmsc.TYPE.value in market_status:
            assert market_status[Ecmsc.TYPE.value] == self.MARKET_STATUS_TYPE, (
                f"market type mismatch: expected {self.MARKET_STATUS_TYPE=!r}, "
                f"got {market_status.get(Ecmsc.TYPE.value)!r} for "
                f"{market_status.get(Ecmsc.SYMBOL.value)!r}"
            )
        symbol = market_status.get(Ecmsc.SYMBOL.value)
        assert symbol is not None, (
            f"market_status missing {Ecmsc.SYMBOL.value!r} (keys: {list(market_status.keys())})"
        )
        allowed_symbols = (
            expected_symbols if expected_symbols is not None
            else (self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3)
        )
        assert symbol in allowed_symbols, (
            f"unexpected market symbol {symbol=!r}: expected one of {allowed_symbols}"
        )
        active_raw = market_status.get(Ecmsc.ACTIVE.value)
        if active_raw is not None:
            expected_active = False if symbol in self.INACTIVE_MARKETS else True
            assert active_raw is expected_active, (
                f"market ACTIVE flag wrong for {symbol=!r}: got {active_raw!r}, expected {expected_active!r}; "
                f"INACTIVE_MARKETS={self.INACTIVE_MARKETS}"
            )
        precision = market_status.get(Ecmsc.PRECISION.value)
        assert isinstance(precision, dict), (
            f"PRECISION must be a dict on market_status for {symbol=} (got {type(precision).__name__}: {precision!r})"
        )

    async def test_get_historical_ohlcv(self):
        # common implementation, should always work if candles history is supported
        historical_ohlcv = await self.get_historical_ohlcv()
        assert len(historical_ohlcv) > 500, (
            f"historical OHLCV stream returned too few rows ({len(historical_ohlcv)}); "
            f"expected more than 500 so multiple paginated fetches likely succeeded"
        )
        self.ensure_elements_order(historical_ohlcv, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        self.ensure_unique_elements(historical_ohlcv, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        start, end = self.get_historical_ohlcv_start_and_end_times()
        max_candle_time = self.get_time_after_time_frames(start, len(historical_ohlcv))
        assert max_candle_time <= end, (
            f"last candle open time window exceeds requested end: {max_candle_time=} {end=} {start=}"
        )
        assert max_candle_time <= self.get_time(), (
            f"last candle open time is in the future relative to now: {max_candle_time=} now={self.get_time()}"
        )
        # on some exchanges, a lot of candles are missing, ensure more than 1 fetch succeeded
        assert (
            self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 0.85
            < len(historical_ohlcv)
            <= self.HISTORICAL_CANDLES_TO_FETCH_COUNT
        ), (
            f"streamed OHLCV length {len(historical_ohlcv)} outside "
            f"({self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 0.85}, {self.HISTORICAL_CANDLES_TO_FETCH_COUNT}] "
            f"(too many gaps or wrong batching; adjust HISTORICAL_CANDLES_TO_FETCH_COUNT or exchange mapping)"
        )
        for candle in historical_ohlcv:
            open_time = candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
            assert start <= open_time <= end, (
                f"candle open timestamp outside [start,end] window: {open_time=} {start=} {end=}"
            )

    def get_config(self):
        return {
            constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE
                }
            }
        }

    def _get_ref_order_book_timestamp(self):
        return time.time() + self.ORDER_BOOK_DESYNC_ALLOWANCE

    async def inner_test_unsupported_get_order_books(self):
        async with (self.get_exchange_manager() as exchange_manager):
            with pytest.raises(trading_errors.NotSupported):
                # with symbols filter
                symbols = [self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3]
                await exchange_manager.exchange.get_order_books(symbols=symbols)

            with pytest.raises(trading_errors.NotSupported):
                # without symbols filter
                await exchange_manager.exchange.get_order_books(symbols=None)

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
        async with (self.get_exchange_manager() as exchange_manager):
            # with symbols filter
            symbols = [self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3]
            books_by_symbol = await exchange_manager.exchange.get_order_books(symbols=symbols)
            ref_time = self._get_ref_order_book_timestamp()
            empty_book_sides = []
            if expected_symbol_filter:
                assert len(books_by_symbol) == len(symbols), (
                    f"filtered get_order_books should return exactly one book per requested symbol; "
                    f"{len(books_by_symbol)=} != {len(symbols)=}, keys={list(books_by_symbol)}"
                )
            else:
                assert len(books_by_symbol) >= expected_missing_symbol_filter_books_min_count, (
                    f"{len(books_by_symbol)} < {expected_missing_symbol_filter_books_min_count}"
                )
            for symbol, book in books_by_symbol.items():
                assert 0 < book[trading_enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value] < ref_time, (
                    f"Invalid {symbol} book timestamp value: "
                    f"{book[trading_enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value]}, {ref_time=}"
                )
                for side in [
                    trading_enums.ExchangeConstantsOrderBookInfoColumns.BIDS,
                    trading_enums.ExchangeConstantsOrderBookInfoColumns.ASKS
                ]:
                    if len(book[side.value]) == 0:
                        empty_book_sides.append((symbol, side))
                    else:
                        assert min_book_orders_count <= len(book[side.value]) <= expected_max_orders_by_side, (
                            f"Unexpected {symbol} {side.value} orders count: {len(book[side.value])}. Expected: "
                            f"[{min_book_orders_count}:{expected_max_orders_by_side}]"
                        )
            if len(empty_book_sides) > max_empty_book_sides:
                raise AssertionError(
                    f"More empty book sides than expected: {max_empty_book_sides=} {empty_book_sides=}"
                )
            # without symbols filter
            if supports_without_symbols_filter:
                books_by_symbol = await exchange_manager.exchange.get_order_books(symbols=None)
                empty_book_sides = []
                assert len(books_by_symbol) >= expected_missing_symbol_filter_books_min_count, (
                    f"{len(books_by_symbol)=} NOT >= {expected_missing_symbol_filter_books_min_count=}"
                )
                for symbol, book in books_by_symbol.items():
                    assert 0 < book[trading_enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value] < ref_time, (
                        f"Invalid {symbol} book timestamp value: "
                        f"{book[trading_enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value]}, {ref_time=}"
                    )
                    for side in [
                        trading_enums.ExchangeConstantsOrderBookInfoColumns.BIDS,
                        trading_enums.ExchangeConstantsOrderBookInfoColumns.ASKS
                    ]:
                        if len(book[side.value]) == 0:
                            empty_book_sides.append((symbol, side))
                        else:
                            assert min_book_orders_count <= len(book[side.value]) <= expected_max_orders_by_side, (
                                f"Unexpected {symbol} {side.value} orders count: {len(book[side.value])}. Expected: "
                                f"[{min_book_orders_count}:{expected_max_orders_by_side}]"
                            )
                if len(empty_book_sides) > max_empty_book_sides:
                    raise AssertionError(
                        f"More empty book sides than expected: {max_empty_book_sides=} {len(empty_book_sides)=}"
                    )
                # with custom limit
                books_by_symbol = await exchange_manager.exchange.get_order_books(symbols=None, limit=custom_limit)
                self._ensure_book_custom_limit(
                    books_by_symbol, supports_custom_limit, expected_max_orders_by_side, custom_limit
                )

    def _ensure_book_custom_limit(
        self,
        books_by_symbol: dict,
        supports_custom_limit: bool,
        no_limit_default_size: int,
        custom_limit: typing.Optional[int],
    ):
        has_taken_limit_into_account = False
        custom_limit = custom_limit or self.DEFAULT_CUSTOM_BOOK_LIMIT
        for symbol, book in books_by_symbol.items():
            for side in [
                trading_enums.ExchangeConstantsOrderBookInfoColumns.BIDS,
                trading_enums.ExchangeConstantsOrderBookInfoColumns.ASKS
            ]:
                if no_limit_default_size < len(book[side.value]) <= custom_limit:
                    has_taken_limit_into_account = True
        if supports_custom_limit:
            assert has_taken_limit_into_account, (
                "expected at least one order book side depth strictly between reference depth and "
                f"custom_limit={custom_limit} (supports_custom_limit=True but limit had no shrinking effect)"
            )
        else:
            assert not supports_custom_limit, "internal mismatch: branching assumes supports_custom_limit is False"

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        async with get_exchange_manager(
            self.EXCHANGE_NAME, config=self.get_config(),
            authenticated=self.REQUIRES_AUTH, market_filter=market_filter,
            uses_tentacle=self.USES_TENTACLE
        ) as exchange_manager:
            yield exchange_manager

    async def time_frames(self):
        async with self.get_exchange_manager() as exchange_manager:
            return exchange_manager.exchange.time_frames

    async def assert_time_frames(self, time_frames: list[commons_enums.TimeFrames]):
        found_time_frames = await self.time_frames()
        for time_frame in time_frames:
            assert time_frame.value in found_time_frames, (
                f"exchange must advertise time frame {time_frame.value!r}; "
                f"only found {sorted(found_time_frames)} (CCXT timeframe map may need update)"
            )
        

    async def test_active_symbols(self):
        raise NotImplementedError("test_active_symbols is not implemented")

    async def assert_supports_order_type(
        self, order_types: typing.Optional[list[trading_enums.TradeOrderType]] = None,
    ):
        order_types = [
            trading_enums.TradeOrderType.MARKET,
            trading_enums.TradeOrderType.LIMIT,
        ] if order_types is None else order_types
        async with self.get_exchange_manager() as exchange_manager:
            for order_type in order_types:
                assert exchange_manager.exchange.supports_order_type(order_type), (
                    f"exchange must support order type {order_type.value!r}"
                )

    async def inner_test_active_symbols(self, expected_active_symbols_count: int, expected_total_symbols_count: int):
        async with self.get_exchange_manager() as exchange_manager:
            # ensure active symbols are correctly parsed by ccxt
            active_symbols = exchange_manager.exchange.get_all_available_symbols(active_only=True)
            assert expected_active_symbols_count <= len(active_symbols) <= expected_active_symbols_count * 1.5, (
                f"CCXT active markets count out of expected band (sanity check parsing vs live exchange): "
                f"{len(active_symbols)} not in "
                f"[{expected_active_symbols_count}, {expected_active_symbols_count * 1.5}]"
            )
            all_symbols = exchange_manager.exchange.get_all_available_symbols(active_only=False)
            assert expected_total_symbols_count <= len(all_symbols) <= expected_total_symbols_count * 1.5, (
                f"CCXT total markets count out of expected band (includes inactive/delisted handling): "
                f"{len(all_symbols)} not in "
                f"[{expected_total_symbols_count}, {expected_total_symbols_count * 1.5}]"
            )
    
    async def assert_get_dex_pairs(
        self,
        symbols: list[str],
        *,
        expected_network: str | None = None,
        expected_dex: str | None = None,
        expected_ticker_symbols: set[str] | None = None,
        min_result_count: int = 1,
        max_price_per_symbol: dict[str, float] | None = None,
        extra_checks: typing.Callable[[list[dict]], None] | None = None,
    ):
        async with self.get_exchange_manager() as exchange_manager:
            dex_pairs = await exchange_manager.exchange.get_dex_pairs(symbols)
            assert len(dex_pairs) >= min_result_count, (
                f"expected at least {min_result_count} dex pairs, got {len(dex_pairs)}"
            )
            for dex_pair in dex_pairs:
                self.check_dex_pair_typing(dex_pair)
            self.check_dex_pairs_no_duplicate_venue_per_pair(dex_pairs)
            if expected_network is not None:
                assert all(
                    dex_pair[Ecdpc.NETWORK.value] == expected_network for dex_pair in dex_pairs
                ), f"expected network {expected_network!r} for all dex pairs"
            if expected_dex is not None:
                assert all(
                    dex_pair[Ecdpc.DEX.value] == expected_dex for dex_pair in dex_pairs
                ), f"expected dex {expected_dex!r} for all dex pairs"
            if expected_ticker_symbols is not None:
                assert {dex_pair[Ecdpc.SYMBOL.value] for dex_pair in dex_pairs} == expected_ticker_symbols, (
                    f"unexpected dex pair symbols: "
                    f"{ {dex_pair[Ecdpc.SYMBOL.value] for dex_pair in dex_pairs} } "
                    f"!= {expected_ticker_symbols}"
                )
            if max_price_per_symbol is not None:
                for dex_pair in dex_pairs:
                    symbol = dex_pair[Ecdpc.SYMBOL.value]
                    max_price = max_price_per_symbol.get(symbol)
                    if max_price is not None:
                        assert dex_pair[Ecdpc.PRICE.value] < max_price, (
                            f"dex pair {symbol} price is too high: "
                            f"{dex_pair[Ecdpc.PRICE.value]} >= {max_price}"
                        )
            if extra_checks is not None:
                extra_checks(dex_pairs)

    async def assert_get_exchange_symbol(
        self,
        expectations: dict[str, tuple[str, str, str]],
    ):
        async with self.get_exchange_manager() as exchange_manager:
            connector_symbols = exchange_manager.exchange.connector.symbols
            for input_symbol, (expected_symbol, expected_base, expected_quote) in expectations.items():
                resolved_symbol = exchange_manager.get_exchange_symbol(input_symbol)
                assert resolved_symbol == expected_symbol
                base, quote = exchange_manager.get_exchange_quote_and_base(input_symbol)
                assert base == expected_base
                assert quote == expected_quote
                assert expected_symbol in connector_symbols, (
                    f"resolved symbol {expected_symbol!r} must be listed in connector.symbols"
                )
                if input_symbol != expected_symbol:
                    assert input_symbol not in connector_symbols, (
                        f"alias input symbol {input_symbol!r} must not be listed in connector.symbols "
                        f"(only its canonical symbol {expected_symbol!r} should)"
                    )

    async def get_market_statuses(self):
        # return 2 different market status with different traded pairs to reduce possible
        # side effects using only one pair.
        async with self.get_exchange_manager() as exchange_manager:
            self._ensure_market_status_cachability(exchange_manager)
            return exchange_manager.exchange.get_market_status(self.SYMBOL), \
                exchange_manager.exchange.get_market_status(self.SYMBOL_2), \
                exchange_manager.exchange.get_market_status(self.SYMBOL_3)
    
    async def assert_get_market_status_not_loaded(self):
        for market_status in await self.get_market_statuses():
            assert market_status == {}, f"market status must be empty, got {market_status!r}"

    async def assert_lazy_loaded_markets(
        self, symbols: list[str], 
        normal_price_max=10000, normal_price_min=1e-06,
        normal_cost_max=10000, normal_cost_min=1e-06,
        low_price_max=1e-07, low_price_min=1e-09,
        low_cost_max=1e-03, low_cost_min=1e-06,
        expect_invalid_price_limit_values=False,
        expect_inferior_or_equal_price_and_cost=False,
        enable_price_and_cost_comparison=True,
        has_price_limits=True,
        extra_checks: typing.Optional[typing.Callable[[dict], None]] = None,
    ):
        # 1. markets are not loaded
        await self.assert_get_market_status_not_loaded()
        # 2. fetching markets for symbols initializes market statuses
        async with self.get_exchange_manager() as exchange_manager:
            fetched_markets = await exchange_manager.exchange.load_markets_for_symbols(symbols)
            resolved_symbols = [
                market_status[Ecmsc.SYMBOL.value] for market_status in fetched_markets
            ]
            expected_market_symbols = list(dict.fromkeys(symbols + resolved_symbols))
            self._check_lazy_loaded_markets(
                fetched_markets,
                symbols,
                loaded_markets=exchange_manager.exchange.connector.client.markets,
            )
            await self.assert_get_market_status(
                normal_price_max=normal_price_max, normal_price_min=normal_price_min,
                normal_cost_max=normal_cost_max, normal_cost_min=normal_cost_min,
                low_price_max=low_price_max, low_price_min=low_price_min,
                low_cost_max=low_cost_max, low_cost_min=low_cost_min,
                expect_invalid_price_limit_values=expect_invalid_price_limit_values,
                expect_inferior_or_equal_price_and_cost=expect_inferior_or_equal_price_and_cost,
                enable_price_and_cost_comparison=enable_price_and_cost_comparison,
                has_price_limits=has_price_limits,
                extra_checks=extra_checks,
                market_statuses=fetched_markets,
                expected_symbols=expected_market_symbols,
            )
            # 3. market statuses are initialized
            market_statuses = [
                exchange_manager.exchange.get_market_status(symbol) for symbol in symbols
            ]
            await self.assert_get_market_status(
                normal_price_max=normal_price_max, normal_price_min=normal_price_min,
                normal_cost_max=normal_cost_max, normal_cost_min=normal_cost_min,
                low_price_max=low_price_max, low_price_min=low_price_min,
                low_cost_max=low_cost_max, low_cost_min=low_cost_min,
                expect_invalid_price_limit_values=expect_invalid_price_limit_values,
                expect_inferior_or_equal_price_and_cost=expect_inferior_or_equal_price_and_cost,
                enable_price_and_cost_comparison=enable_price_and_cost_comparison,
                has_price_limits=has_price_limits,
                extra_checks=extra_checks,
                market_statuses=market_statuses,
                expected_symbols=expected_market_symbols,
            )
    
    def _check_lazy_loaded_markets(
        self,
        markets: list[dict],
        symbols: list[str],
        loaded_markets: dict | None = None,
    ):
        assert len(markets) == len(symbols), (
            f"expected one market status per requested symbol, got {len(markets)} for {len(symbols)} symbols"
        )
        for market_status in markets:
            assert market_status.get(Ecmsc.SYMBOL.value), (
                f"market status must include a non-empty symbol: {market_status!r}"
            )
        if loaded_markets is not None:
            for symbol in symbols:
                assert symbol in loaded_markets, (
                    f"requested symbol {symbol!r} not present in connector markets"
                )
            self.check_markets_no_duplicate_venue_per_pair(loaded_markets)

    async def assert_get_market_status(
        self,
        normal_price_max=10000, normal_price_min=1e-06,
        normal_cost_max=10000, normal_cost_min=1e-06,
        low_price_max=1e-07, low_price_min=1e-09,
        low_cost_max=1e-03, low_cost_min=1e-06,
        expect_invalid_price_limit_values=False,
        expect_inferior_or_equal_price_and_cost=False,
        enable_price_and_cost_comparison=True,
        has_price_limits=True,
        extra_checks: typing.Optional[typing.Callable[[dict], None]] = None,
        market_statuses: typing.Optional[dict[str, dict]] = None,
        expected_symbols: list[str] | None = None,
    ):
        for market_status in (market_statuses or await self.get_market_statuses()):
            self.ensure_required_market_status_values(market_status, expected_symbols=expected_symbols)
            # market statuses should always be valid: fixer is automatically applied when ob_exchange requires it
            symbol = market_status[Ecmsc.SYMBOL.value]
            precision = market_status[Ecmsc.PRECISION.value]
            amount_precision = precision[Ecmsc.PRECISION_AMOUNT.value]
            price_precision = precision[Ecmsc.PRECISION_PRICE.value]
            try:
                _market_precision_decimal_places_or_tick(amount_precision)
            except AssertionError as exc:
                raise AssertionError(f"amount precision invalid ({symbol=}): {exc}") from exc
            try:
                _market_precision_decimal_places_or_tick(price_precision)
            except AssertionError as exc:
                raise AssertionError(f"price precision invalid ({symbol=}): {exc}") from exc
            limits = market_status[Ecmsc.LIMITS.value]
            required_limit_keys = (Ecmsc.LIMITS_AMOUNT.value, Ecmsc.LIMITS_PRICE.value, Ecmsc.LIMITS_COST.value)
            assert all(elem in limits for elem in required_limit_keys), (
                f"LIMITS subtree missing AMOUNT/PRICE/COST buckets ({symbol=} keys={list(limits)})"
            )
            self.check_market_status_limits(
                market_status,
                normal_price_max=normal_price_max, normal_price_min=normal_price_min,
                normal_cost_max=normal_cost_max, normal_cost_min=normal_cost_min,
                low_price_max=low_price_max, low_price_min=low_price_min,
                low_cost_max=low_cost_max, low_cost_min=low_cost_min,
                expect_invalid_price_limit_values=expect_invalid_price_limit_values,
                expect_inferior_or_equal_price_and_cost=expect_inferior_or_equal_price_and_cost,
                enable_price_and_cost_comparison=enable_price_and_cost_comparison,
                has_price_limits=has_price_limits
            )
            if extra_checks:
                extra_checks(market_status)

    async def assert_market_status(self):
        for market_status in await self.get_market_statuses():
            self.ensure_required_market_status_values(market_status)
            # market statuses should always be valid: fixer is automatically applied when
            # ob_exchange requires it
            symbol = market_status[Ecmsc.SYMBOL.value]
            precision = market_status[Ecmsc.PRECISION.value]
            amount_precision = precision[Ecmsc.PRECISION_AMOUNT.value]
            price_precision = precision[Ecmsc.PRECISION_PRICE.value]
            try:
                _market_precision_decimal_places_or_tick(amount_precision)
            except AssertionError as exc:
                raise AssertionError(f"amount precision invalid ({symbol=}): {exc}") from exc
            try:
                _market_precision_decimal_places_or_tick(price_precision)
            except AssertionError as exc:
                raise AssertionError(f"price precision invalid ({symbol=}): {exc}") from exc
            limits = market_status[Ecmsc.LIMITS.value]
            required_limit_keys = (Ecmsc.LIMITS_AMOUNT.value, Ecmsc.LIMITS_PRICE.value, Ecmsc.LIMITS_COST.value)
            assert all(elem in limits for elem in required_limit_keys), (
                f"LIMITS subtree missing AMOUNT/PRICE/COST buckets ({symbol=} keys={list(limits)})"
            )

    def _ensure_market_status_cachability(self, exchange_manager):
        exchange_class = ccxt_client_util.ccxt_exchange_class_factory(self.EXCHANGE_NAME)
        client_using_cached_markets = exchange_class(
            ccxt_client_util.get_custom_domain_config(exchange_class) # use custom domain config if set
        )
        if not exchange_manager.exchange.get_option_value(trading_enums.ExchangeClientOptions.SUPPORTS_MARKETS_CACHE):
            with pytest.raises(KeyError):
                ccxt_client_util.load_markets_from_cache(client_using_cached_markets, False)
            return
        ccxt_client_util.load_markets_from_cache(client_using_cached_markets, False)
        cached = client_using_cached_markets.markets
        actual = exchange_manager.exchange.connector.client.markets
        assert actual == cached, (
            "live connector markets dict must equal CCXT markets loaded from the same cache file "
            f"(sizes {len(actual)} vs {len(cached)})"
        )

    async def get_symbol_prices(self, limit=None, **kwargs):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_symbol_prices(
                self.SYMBOL, self.TIME_FRAME, limit=limit, **kwargs
            )
    
    async def assert_get_symbol_prices(
        self,
        default_limit: int = 100,
        tested_limit: int = 150,
        *,
        default_allowed_lengths: tuple[int, ...] | None = None,
        default_min_length: int | None = None,
        tested_limit_min: int | None = None,
        symbol_prices_kwargs: dict | None = None,
        expect_recent_last_candle: bool = True,
    ):
        # without limit
        call_kwargs = symbol_prices_kwargs or {}
        symbol_prices = await self.get_symbol_prices(limit=None, **call_kwargs)
        assert symbol_prices is not None and len(symbol_prices) > 0, (
            f"exchange must return OHLCV when limit=None: {symbol_prices=}"
        )
        if default_min_length is not None:
            assert len(symbol_prices) > default_min_length, (
                f"default fetch returned too few candles: {len(symbol_prices)} not > {default_min_length} "
                f"(exchange-specific minimum row count check)"
            )
        elif default_allowed_lengths is not None:
            assert len(symbol_prices) in default_allowed_lengths, (
                f"default fetch row count {len(symbol_prices)} not an allowed length {default_allowed_lengths=} "
                f"(exchange batch size changed)"
            )
        else:
            assert len(symbol_prices) == default_limit, (
                f"default fetch must return exactly default_limit={default_limit} rows "
                f"(got {len(symbol_prices)}; pass default_min_length or default_allowed_lengths if the "
                f"exchange batches differently)"
            )
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        last_candle = symbol_prices[-1]
        assert last_candle is not None, "last default-limit candle row must not be None"
        if expect_recent_last_candle:
            earliest_allowed = self.get_time() - self.get_allowed_time_delta()
            assert last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] >= earliest_allowed, (
                f"last candle is too stale: timestamp={last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]} "
                f"earliest_allowed={earliest_allowed}"
            )

        # try with candles limit (used in candled updater)
        symbol_prices = await self.get_symbol_prices(limit=tested_limit, **call_kwargs)
        if tested_limit_min is None:
            assert symbol_prices is not None and len(symbol_prices) == tested_limit, (
                f"explicit candle limit request must return exactly {tested_limit} rows "
                f"(got {len(symbol_prices) if symbol_prices is not None else None})"
            )
        else:
            assert symbol_prices is not None and tested_limit_min <= len(symbol_prices) <= tested_limit, (
                f"candle count with explicit limit must fall in [{tested_limit_min}, {tested_limit}] "
                f"(exchange may cap or shorten responses; got {len(symbol_prices) if symbol_prices is not None else None})"
            )
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        last_candle = symbol_prices[-1]
        assert last_candle is not None, "last candle row from explicit limit fetch must not be None"
        if expect_recent_last_candle:
            earliest_allowed = self.get_time() - self.get_allowed_time_delta()
            assert last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] >= earliest_allowed, (
                f"last candle after explicit limit fetch is too stale: "
                f"timestamp={last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]} "
                f"earliest_allowed={earliest_allowed}"
            )

    async def assert_get_symbol_prices_empty_default_then_limit(
        self, tested_limit: int = 200, *, symbol_prices_kwargs: dict | None = None
    ):
        """Some exchanges return no candles when limit is omitted but honor an explicit limit (e.g. NDAX)."""
        call_kwargs = symbol_prices_kwargs or {}
        symbol_prices = await self.get_symbol_prices(limit=None, **call_kwargs)
        assert len(symbol_prices) == 0, (
            f"exchange must return no rows when limit=None for this contract (NDAX-style); got {len(symbol_prices)} rows"
        )
        symbol_prices = await self.get_symbol_prices(limit=tested_limit, **call_kwargs)
        assert symbol_prices is not None and len(symbol_prices) == tested_limit, (
            f"explicit limit fetch must return exactly {tested_limit} rows "
            f"(got {len(symbol_prices) if symbol_prices is not None else None})"
        )
        self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
        last_candle = symbol_prices[-1]
        assert last_candle is not None, "last candle row must not be None (empty-default-then-limit exchanges)"
        earliest_allowed = self.get_time() - self.get_allowed_time_delta()
        assert last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] >= earliest_allowed, (
            f"last candle timestamp too old for current window: "
            f"{last_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]} < {earliest_allowed}"
        )

    async def get_historical_ohlcv(self, **kwargs) -> list:
        async with self.get_exchange_manager() as exchange_manager:
            start, end = self.get_historical_ohlcv_start_and_end_times()
            start_ms, end_ms = start * 1000, end * 1000
            ohlcvs = []
            async for ohlcv in exchanges_util.get_historical_ohlcv(
                exchange_manager, self.SYMBOL, self.TIME_FRAME, start_ms, end_ms, request_retry_timeout=2, **kwargs
            ):
                ohlcvs.extend(ohlcv)
            return ohlcvs
    
    async def assert_get_historical_ohlcv(
        self,
        *,
        max_candle_upper_time: typing.Callable[[], float] | None = None,
        cap_time_extra_seconds: float = 0,
        candle_lower_slack_seconds: float = 0,
        candle_upper_slack_seconds: float = 0,
        require_each_open_time_not_before_since: bool = True,
    ):
        # try with since and limit (used in data collector)
        for limit in (50, None):
            symbol_prices = await self.get_symbol_prices(since=self.CANDLE_SINCE, limit=limit)
            assert symbol_prices is not None, (
                f"get_symbol_prices with since must return a list, not None ({limit=!r} {self.CANDLE_SINCE=!r})"
            )
            if limit:
                assert len(symbol_prices) == limit, (
                    f"with fixed limit and since, row count must equal limit={limit} "
                    f"(got {len(symbol_prices)})"
                )
            else:
                assert len(symbol_prices) > 5, (
                    f"unbounded historical fetch should return more than a trivial number of rows "
                    f"(got {len(symbol_prices)} for {self.CANDLE_SINCE=!r})"
                )
            # check candles order (oldest first)
            self.ensure_elements_order(symbol_prices, commons_enums.PriceIndexes.IND_PRICE_TIME.value)
            # check that fetched candles are historical candles
            max_candle_time = self.get_time_after_time_frames(self.CANDLE_SINCE_SEC, len(symbol_prices))
            cap_time = self.get_time() if max_candle_upper_time is None else max_candle_upper_time()
            cap_time += cap_time_extra_seconds
            assert max_candle_time <= cap_time, (
                f"theoretical end of fetched range exceeds allowed cap ({max_candle_time=} > {cap_time=}); "
                f"since={self.CANDLE_SINCE_SEC} rows={len(symbol_prices)}; "
                f"raise cap_time_extra_seconds if the exchange advances the theoretical window slightly"
            )
            time_idx = commons_enums.PriceIndexes.IND_PRICE_TIME.value
            span_end_after_last_bar = symbol_prices[-1][time_idx] + self.get_timeframe_seconds()
            range_upper_model = max(max_candle_time, span_end_after_last_bar)
            range_low = self.CANDLE_SINCE_SEC - candle_lower_slack_seconds
            range_high = range_upper_model + candle_upper_slack_seconds
            for candle in symbol_prices:
                assert candle is not None, "OHLCV row must not be None inside the fetched list"
                open_time = candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                assert open_time <= range_high, (
                    f"candle open time exceeds allowed upper bound (+ slack): "
                    f"{open_time=} {range_high=} {range_upper_model=} {max_candle_time=} "
                    f"{candle_upper_slack_seconds=}"
                )
                if require_each_open_time_not_before_since:
                    assert open_time >= range_low, (
                        f"candle open time before requested since boundary (- slack): "
                        f"{open_time=} {range_low=} since={self.CANDLE_SINCE_SEC} "
                        f"{candle_lower_slack_seconds=}"
                    )

    def get_historical_ohlcv_start_and_end_times(self):
        start = self.get_time() - (self.get_timeframe_seconds() * self.HISTORICAL_CANDLES_TO_FETCH_COUNT * 2)
        end = self.get_time_after_time_frames(start, self.HISTORICAL_CANDLES_TO_FETCH_COUNT)
        return start, end

    async def get_kline_price(self, time_frame=None, **kwargs):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_kline_price(self.SYMBOL, time_frame or self.TIME_FRAME, **kwargs)

    async def assert_get_kline_price(
        self,
        time_frame=None,
        *,
        require_recent_open_time: bool = True,
        **kwargs,
    ):
        kline_price = await self.get_kline_price(time_frame=time_frame, **kwargs)
        assert kline_price is not None, "get_kline_price must return a list, not None"
        assert len(kline_price) == 1, (
            f"kline response must be a single current candle row (got {len(kline_price)} rows)"
        )
        kline_row = kline_price[0]
        assert kline_row is not None, "kline row must not be None"
        assert len(kline_row) == 6, (
            f"each kline row must have 6 OHLCV fields (got {len(kline_row)} columns)"
        )
        kline_start_time = kline_row[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
        if require_recent_open_time:
            earliest = self.get_time() - self.get_allowed_time_delta()
            assert kline_start_time >= earliest, (
                f"kline start time too far in the past to be the current candle: "
                f"{kline_start_time=} earliest_allowed={earliest}"
            )

    async def get_order_book(self, **kwargs):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_order_book(self.SYMBOL, **kwargs)

    async def assert_get_order_book(
        self,
        limit: int | None = 20,
        *,
        order_book_entry_length: int = 2,
        depth_mode: typing.Literal["exact", "minimum", "strictly_greater_than", "range"] = "exact",
        min_orders_per_side: int | None = None,
        max_orders_per_side: int | None = None,
        strictly_greater_than: int | None = None,
        allow_empty_book_side: bool = False,
    ):
        ecobic = trading_enums.ExchangeConstantsOrderBookInfoColumns
        if limit is None:
            order_book = await self.get_order_book()
        else:
            order_book = await self.get_order_book(limit=limit)
        assert order_book is not None, "get_order_book must return a dict, not None"
        book_ts = order_book[ecobic.TIMESTAMP.value]
        ref_ts = self._get_ref_order_book_timestamp()
        assert 0 < book_ts < ref_ts, (
            f"order book timestamp must be a fresh Unix time in (0, ref): {book_ts=} {ref_ts=} {limit=!r}"
        )

        def _assert_side_depth(side: trading_enums.ExchangeConstantsOrderBookInfoColumns) -> None:
            rows = order_book[side.value]
            side_len = len(rows)
            if depth_mode == "exact":
                assert limit is not None, "depth_mode='exact' requires a non-None limit argument"
                assert side_len == limit, (
                    f"order book {side.value} depth must match requested limit={limit} in exact mode "
                    f"(got {side_len} rows)"
                )
            elif depth_mode == "minimum":
                assert min_orders_per_side is not None, (
                    "depth_mode='minimum' requires min_orders_per_side"
                )
                assert side_len >= min_orders_per_side, (
                    f"order book {side.value} must expose at least min_orders_per_side={min_orders_per_side} "
                    f"(got {side_len})"
                )
            elif depth_mode == "strictly_greater_than":
                assert strictly_greater_than is not None, (
                    "depth_mode='strictly_greater_than' requires strictly_greater_than"
                )
                assert side_len > strictly_greater_than, (
                    f"order book {side.value} must be deeper than strictly_greater_than={strictly_greater_than} "
                    f"(got {side_len})"
                )
            elif depth_mode == "range":
                assert min_orders_per_side is not None and max_orders_per_side is not None, (
                    "depth_mode='range' requires both min_orders_per_side and max_orders_per_side"
                )
                assert min_orders_per_side <= side_len <= max_orders_per_side, (
                    f"order book {side.value} depth must fall in "
                    f"[{min_orders_per_side}, {max_orders_per_side}] (got {side_len})"
                )
            if side_len == 0 and allow_empty_book_side:
                return
            first_row = rows[0]
            assert first_row is not None, f"{side.value} first order book row must not be None"
            assert len(first_row) == order_book_entry_length, (
                f"{side.value} row must contain {order_book_entry_length} cells [price, amount]; "
                f"got length {len(first_row)}"
            )

        _assert_side_depth(ecobic.ASKS)
        _assert_side_depth(ecobic.BIDS)

    async def assert_order_book_custom_limit(
        self,
        custom_limit: int,
        *,
        supports_custom_limit: bool,
        reference_no_limit_depth: int,
    ):
        custom_limit_order_book = await self.get_order_book(limit=custom_limit)
        self._ensure_book_custom_limit(
            {self.SYMBOL: custom_limit_order_book},
            supports_custom_limit,
            reference_no_limit_depth,
            custom_limit,
        )

    async def get_recent_trades(self, limit=50):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_recent_trades(self.SYMBOL, limit=limit)
    
    async def assert_get_recent_trades(self, limit=50):
        recent_trades = await self.get_recent_trades(limit=limit)
        assert len(recent_trades) == limit, (
            f"get_recent_trades(limit={limit}) must return exactly {limit} trades "
            f"(got {len(recent_trades)}; paging or filtering may differ on this exchange)"
        )
        self.ensure_elements_order(recent_trades, trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value)

    async def get_price_ticker(self, symbol: typing.Optional[str] = None):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_price_ticker(symbol or self.SYMBOL)

    async def assert_get_price_ticker(
        self,
        extra_checks: typing.Optional[typing.Callable[[dict], None]] = None,
        *,
        symbol: typing.Optional[str] = None,
        ticker_expectations: typing.Optional[TickerRequiredExpectations] = None,
    ):
        symbol = symbol or self.SYMBOL
        async with self.get_exchange_manager() as exchange_manager:
            no_volume_in_ticker = exchange_manager.exchange.get_option_value(
                trading_enums.ExchangeClientOptions.NO_VOLUME_IN_TICKER
            )
            ticker = await exchange_manager.exchange.get_price_ticker(symbol)
        self._check_ticker(
            ticker, symbol, extra_checks=extra_checks, no_volume_in_ticker=no_volume_in_ticker,
        )
        self._check_ticker_required_content(
            ticker, ticker_expectations=ticker_expectations, no_volume_in_ticker=no_volume_in_ticker,
        )

    @classmethod
    def _check_ticker(
        cls,
        ticker, symbol,
        extra_checks: typing.Optional[typing.Callable[[dict], None]] = None,
        allowed_failed_tickers_typing_checks_percentage: int = 0,
        no_volume_in_ticker: bool = False,
    ):
        assert ticker[Ectc.SYMBOL.value] == symbol, (
            f"ticker symbol mismatch: expected {symbol!r}, got {ticker.get(Ectc.SYMBOL.value)!r}"
        )
        required_columns = (
            Ectc.HIGH.value,
            Ectc.LOW.value,
            Ectc.BID.value,
            Ectc.BID_VOLUME.value,
            Ectc.ASK.value,
            Ectc.ASK_VOLUME.value,
            Ectc.OPEN.value,
            Ectc.CLOSE.value,
            Ectc.LAST.value,
            Ectc.PREVIOUS_CLOSE.value,
        )
        missing = [key for key in required_columns if key not in ticker]
        assert not missing, f"ticker dict missing required columns {missing} (have keys {list(ticker)})"
        failed_tickers_count = 0
        allowed_failed_tickers_typing_checks = len(ticker) * allowed_failed_tickers_typing_checks_percentage / 100
        try:
            cls.check_ticker_typing(
                ticker,
                check_close=True, # check close and timestamp only
                check_open=False, check_high=False, check_low=False, check_base_volume=False, check_last=True
            )
        except AssertionError as e:
            failed_tickers_count += 1
            if failed_tickers_count > allowed_failed_tickers_typing_checks:
                raise AssertionError(
                    f"ticker {symbol} typing check failed: {e} (allowed "
                    f"{allowed_failed_tickers_typing_checks_percentage}% failed tickers, "
                    f"{failed_tickers_count} failed out of {len(ticker)} tickers)"
                )
        if extra_checks:
            extra_checks(ticker)

    @staticmethod
    def _apply_ticker_content_expectation(column: str, value, expect: TickerExpect):
        if expect == TickerExpect.SKIP:
            return
        if expect == TickerExpect.TRUTHY:
            assert value, f"ticker[{column}] expected truthy, got {value!r}"
            return
        if expect == TickerExpect.NONE:
            assert value is None, f"ticker[{column}] expected None, got {value!r}"
            return
        if expect == TickerExpect.NOT_NONE:
            assert value is not None, f"ticker[{column}] expected not None"
            return
        raise AssertionError(f"Unhandled TickerExpect enum value for column {column!r}: {expect!r}")

    @classmethod
    def _check_ticker_required_content(
        cls,
        ticker,
        *,
        ticker_expectations: typing.Optional[TickerRequiredExpectations] = None,
        no_volume_in_ticker: bool = False,
    ):
        content = _merge_ticker_content_expectations(ticker_expectations, no_volume_in_ticker=no_volume_in_ticker)
        for column, expect in content.items():
            if expect == TickerExpect.SKIP:
                continue
            assert column in ticker, (
                f"ticker missing column {column!r} required by merged TickerRequiredExpectations "
                f"(present keys: {list(ticker)})"
            )
            cls._apply_ticker_content_expectation(column, ticker[column], expect)

    async def get_all_currencies_price_ticker(self, **kwargs):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_all_currencies_price_ticker(**kwargs)

    async def assert_get_all_currencies_price_ticker(
        self,
        symbols: typing.Optional[list[str]] = None,
        extra_checks: typing.Optional[typing.Callable[[dict], None]] = None,
        allowed_failed_tickers_typing_checks_percentage: int = 0,
        ticker_expectations: typing.Optional[TickerRequiredExpectations] = None,
    ):
        async with self.get_exchange_manager() as exchange_manager:
            no_volume_in_ticker = exchange_manager.exchange.get_option_value(
                trading_enums.ExchangeClientOptions.NO_VOLUME_IN_TICKER
            )
            tickers = await exchange_manager.exchange.get_all_currencies_price_ticker(symbols=symbols)
        if symbols:
            assert sorted(tickers.keys()) == sorted(symbols)
        for symbol, ticker in tickers.items():
            self._check_ticker(
                ticker, symbol,
                extra_checks=extra_checks,
                allowed_failed_tickers_typing_checks_percentage=allowed_failed_tickers_typing_checks_percentage,
                no_volume_in_ticker=no_volume_in_ticker,
            )
            if ticker_expectations is not None or no_volume_in_ticker:
                self._check_ticker_required_content(
                    ticker,
                    ticker_expectations=ticker_expectations,
                    no_volume_in_ticker=no_volume_in_ticker,
                )

    async def get_user_recent_trades(self):
        async with self.get_exchange_manager() as exchange_manager:
            return await exchange_manager.exchange.get_user_recent_trades(self.SYMBOL)

    def get_market_filter(self):
        def market_filter(market):
            return (
                market[trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value]
                in (self.SYMBOL, self.SYMBOL_2)
            )

        return market_filter

    def get_allowed_time_delta(self):
        return (self.ALLOWED_TIMEFRAMES_WITHOUT_CANDLE + 1) * \
            commons_enums.TimeFramesMinutes[self.TIME_FRAME] * \
            constants.MINUTE_TO_SECONDS * 1.3

    @staticmethod
    def get_time():
        return Exchange.seconds()

    @staticmethod
    def get_ms_time():
        return int(Exchange.milliseconds())

    def get_timeframe_seconds(self):
        return commons_enums.TimeFramesMinutes[self.TIME_FRAME] * constants.MINUTE_TO_SECONDS

    def get_time_after_time_frames(self, start, time_frames_count):
        return start + self.get_timeframe_seconds() * time_frames_count

    def get_timeframe_ms_delta(self, time_frames_count):
        return self.get_ms_time() - (self.get_timeframe_seconds() * time_frames_count * constants.MSECONDS_TO_SECONDS)

    @staticmethod
    def ensure_elements_order(elements, sort_key, reverse=False):
        assert sorted(elements, key=lambda x: x[sort_key], reverse=reverse) == elements, (
            f"elements must be sorted by {sort_key!r} reverse={reverse}; "
            f"first divergence vs sorted order indicates out-of-order exchange data"
        )

    @staticmethod
    def ensure_unique_elements(elements, key):
        assert len(elements) == len(set(element[key] for element in elements)), (
            f"duplicate values for key {key!r}: each element must be uniquely identified by that field"
        )

    def check_market_status_limits(self, market_status,
                                   normal_price_max=10000, normal_price_min=1e-06,
                                   normal_cost_max=10000, normal_cost_min=1e-06,
                                   low_price_max=1e-07, low_price_min=1e-09,
                                   low_cost_max=1e-03, low_cost_min=1e-06,
                                   expect_invalid_price_limit_values=False,
                                   expect_inferior_or_equal_price_and_cost=False,
                                   enable_price_and_cost_comparison=True,
                                   has_price_limits=True):
        min_price = market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MIN.value]
        max_price = market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MAX.value]
        min_cost = market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]
        has_min_or_max_price = min_price not in (None, 0) or max_price not in (None, 0)
        if has_min_or_max_price and not has_price_limits:
            raise AssertionError(
                f"Expect no price limit values but min or max price limit is set (min: {min_price} max: {max_price})"
            )
        if not has_min_or_max_price and has_price_limits:
            raise AssertionError(
                f"Expect price limit values but min or max price limit is not set (min: {min_price} max: {max_price})"
            )
        has_price_limit_value = min_price not in (None, 0)
        has_cost_limit_value = min_cost not in (None, 0)
        has_limit_value = has_price_limit_value and has_cost_limit_value
        if (not has_limit_value) and expect_invalid_price_limit_values:
            raise AssertionError("No price and limit value does not mean invalid values")
        if not expect_invalid_price_limit_values and market_status[Ecmsc.SYMBOL.value] == self.SYMBOL_3:
            # if these test are not passing, it means that limits are invalid
            # (limits should be much lower for SYMBOL_3 which is the low price pair, ex: XRP/BTC)
            # => set expect_invalid_price_limit_values to True in call and
            # remove price limit in exchange tentacle market status fixer if this is the case
            if has_price_limit_value:
                assert (not has_price_limit_value) or low_price_max >= min_price >= low_price_min, (
                    f"SYMBOL_3 min price must sit in low-price micro-instrument band: "
                    f"need {low_price_max} >= {min_price} >= {low_price_min} "
                    f"({market_status[Ecmsc.SYMBOL.value]=}; lower expect_invalid_price_limit_values or widen bounds)"
                )
            assert (not has_cost_limit_value) or low_cost_max >= min_cost >= low_cost_min, (
                f"SYMBOL_3 min cost must sit in low-cost band: need {low_cost_max} >= {min_cost} >= {low_cost_min} "
                f"({market_status[Ecmsc.SYMBOL.value]=})"
            )
        else:
            if has_price_limit_value:
                assert (not has_price_limit_value) or normal_price_max >= min_price >= normal_price_min, (
                    f"min price must lie in the normal pair band: "
                    f"{normal_price_max} >= {min_price} >= {normal_price_min} "
                    f"({market_status[Ecmsc.SYMBOL.value]=})"
                )
            assert (not has_cost_limit_value) or normal_cost_max >= min_cost >= normal_cost_min, (
                f"min cost must lie in the normal pair band: "
                f"{normal_cost_max} >= {min_cost} >= {normal_cost_min} "
                f"({market_status[Ecmsc.SYMBOL.value]=})"
            )
        if has_price_limits and enable_price_and_cost_comparison and has_limit_value:
            # Consistency here is not required by OctoBot. Fix in tentacles if consistency
            # in price/cost comparison becomes required and min_price <= min_cost is false without a good reason
            assert min_price is not None and min_cost is not None, (
                "price/cost consistency check requires non-None min_price and min_cost "
                f"({market_status[Ecmsc.SYMBOL.value]=})"
            )
            if expect_inferior_or_equal_price_and_cost:
                assert min_price >= min_cost, (
                    f"expected min_price >= min_cost when expect_inferior_or_equal_price_and_cost=True "
                    f"({min_price=} {min_cost=} {market_status[Ecmsc.SYMBOL.value]=})"
                )
            else:
                assert min_price <= min_cost, (
                    f"expected min_price <= min_cost (common lot vs notional relation); "
                    f"set enable_price_and_cost_comparison=False if exchange omits this "
                    f"({min_price=} {min_cost=} {market_status[Ecmsc.SYMBOL.value]=})"
                )

    @classmethod
    def check_dex_pair_typing(cls, dex_pair: dict):
        required_columns = (
            Ecdpc.SYMBOL,
            Ecdpc.NETWORK,
            Ecdpc.DEX,
            Ecdpc.BASE_TOKEN_ADDRESS,
            Ecdpc.QUOTE_TOKEN_ADDRESS,
            Ecdpc.PRICE,
            Ecdpc.QUOTE_LIQUIDITY,
        )
        for column in required_columns:
            assert column.value in dex_pair, (
                f"dex pair missing required column {column.value!r}: {dex_pair!r}"
            )
        string_columns = (
            Ecdpc.SYMBOL,
            Ecdpc.NETWORK,
            Ecdpc.DEX,
            Ecdpc.BASE_TOKEN_ADDRESS,
            Ecdpc.QUOTE_TOKEN_ADDRESS,
        )
        for column in string_columns:
            value = dex_pair[column.value]
            assert isinstance(value, str) and value, (
                f"dex pair {column.value} must be a non-empty string; got {value!r}"
            )
        for column in (Ecdpc.PRICE, Ecdpc.QUOTE_LIQUIDITY):
            value = dex_pair[column.value]
            assert isinstance(value, decimal.Decimal), (
                f"dex pair {column.value} must be decimal.Decimal; got {type(value).__name__} {value!r}"
            )
            assert value > 0, (
                f"dex pair {column.value} must be > 0; got {value!r}"
            )

    @classmethod
    def check_dex_pairs_no_duplicate_venue_per_pair(cls, dex_pairs: list[dict]) -> None:
        seen_pair_venue_keys: set[tuple[str, str, str]] = set()
        duplicate_pair_venue_keys: list[tuple[str, str, str]] = []
        for dex_pair in dex_pairs:
            pair_venue_key = (
                dex_pair[Ecdpc.SYMBOL.value],
                dex_pair[Ecdpc.NETWORK.value],
                dex_pair[Ecdpc.DEX.value],
            )
            if pair_venue_key in seen_pair_venue_keys:
                duplicate_pair_venue_keys.append(pair_venue_key)
            else:
                seen_pair_venue_keys.add(pair_venue_key)
        assert not duplicate_pair_venue_keys, (
            f"duplicate venues for a pair: {duplicate_pair_venue_keys}"
        )

    @classmethod
    def check_markets_no_duplicate_venue_per_pair(cls, markets: dict) -> None:
        unique_markets_by_id: dict[str, dict] = {}
        for market in markets.values():
            market_id = market.get(Ecmsc.ID.value)
            if market_id and market_id not in unique_markets_by_id:
                unique_markets_by_id[market_id] = market
        seen_pair_venue_keys: set[tuple[str, str, str]] = set()
        duplicate_pair_venue_keys: list[tuple[str, str, str]] = []
        for market in unique_markets_by_id.values():
            base = market.get(Ecmsc.CURRENCY.value)
            quote = market.get(Ecmsc.MARKET.value)
            market_id = market.get(Ecmsc.ID.value, '')
            id_parts = market_id.split(':') if market_id else []
            network_code = id_parts[0] if len(id_parts) > 0 else ''
            dex_code = id_parts[1] if len(id_parts) > 1 else ''
            pair_venue_key = (f"{base}/{quote}", network_code, dex_code)
            if pair_venue_key in seen_pair_venue_keys:
                duplicate_pair_venue_keys.append(pair_venue_key)
            else:
                seen_pair_venue_keys.add(pair_venue_key)
        assert not duplicate_pair_venue_keys, (
            f"duplicate venues for a market pair: {duplicate_pair_venue_keys}"
        )

    @classmethod
    def check_ticker_typing(
        cls,
        ticker, check_open=True, check_high=True, check_low=True,
        check_close=True, check_last=False, check_base_volume=True,
        check_quote_volume=False
    ):
        symbol = ticker.get(Ectc.SYMBOL.value)
        assert symbol, f"ticker symbol must be set: {ticker!r}"
        # timestamp must always be set
        value = ticker[Ectc.TIMESTAMP.value]
        assert isinstance(value, (float, int)), (
            f"ticker timestamp must be numeric epoch; got {type(value).__name__} {value!r}"
        )
        # ensure timestamp is within 24 hours of current time and is in seconds
        assert (
            cls.MIN_TICKERS_TIMESTAMP_ALLOWANCE
            <= ticker[Ectc.TIMESTAMP.value]
            <= time.time() + constants.DAYS_TO_SECONDS
        ), (
            f"{symbol} ticker timestamp must be within {constants.DAYS_TO_SECONDS} seconds of current time: "
            f"{cls.MIN_TICKERS_TIMESTAMP_ALLOWANCE} <= {ticker[Ectc.TIMESTAMP.value]} <= {time.time() + constants.DAYS_TO_SECONDS}"
        )
        has_volume = ticker.get(Ectc.BASE_VOLUME.value) or ticker.get(Ectc.QUOTE_VOLUME.value)
        if check_open:
            value = ticker[Ectc.OPEN.value]
            assert isinstance(value, (float, int)), (
                f"ticker open must be numeric for typing check; got {type(value).__name__} {value!r}"
            )
        if check_high:
            value = ticker[Ectc.HIGH.value]
            assert isinstance(value, (float, int)), (
                f"ticker high must be numeric; got {type(value).__name__} {value!r}"
            )
        if check_low:
            value = ticker[Ectc.LOW.value]
            assert isinstance(value, (float, int)), (
                f"ticker low must be numeric; got {type(value).__name__} {value!r}"
            )
        if check_close:
            value = ticker[Ectc.CLOSE.value]
            if has_volume:
                expected_type = (float, int)
            else:
                expected_type = (float, int, NoneType) # close can be None when no volume
            assert isinstance(value, tuple(expected_type)), (
                f"{symbol} ticker close must be {tuple(expected_type)!r}; got {type(value).__name__} {value!r}"
            )
        if check_last:
            value = ticker[Ectc.LAST.value]
            if has_volume:
                expected_type = (float, int)
            else:
                expected_type = (float, int, NoneType) # last can be None when no volume
            assert isinstance(value, tuple(expected_type)), (
                f"{symbol} ticker last must be {tuple(expected_type)!r}; got {type(value).__name__} {value!r}"
            )
        if check_base_volume:
            value = ticker[Ectc.BASE_VOLUME.value]
            assert isinstance(value, (float, int)), (
                f"ticker base volume must be numeric; got {type(value).__name__} {value!r}"
            )
        if check_quote_volume:
            value = ticker[Ectc.QUOTE_VOLUME.value]
            assert isinstance(value, (float, int)), (
                f"ticker quote volume must be numeric; got {type(value).__name__} {value!r}"
            )
