import math
import time

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.api as trading_api
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.util.exchange_util as exchange_util

import octobot_flow.constants as flow_constants

logger = commons_logging.get_logger("DailyPriceCacheUpdater")


async def update_daily_prices(
    exchange_manager,
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    symbols: list[str],
    data_root: str = None,
) -> None:
    """
    Fetch daily OHLCV candles for the given reference symbols and merge close prices
    into the persisted daily price cache under exchange-native fetch symbols.
    """
    daily_prices = await trading_api.load_daily_prices(
        exchange_name, exchange_type, sandboxed, data_root
    )

    for reference_symbol in symbols:
        parsed = _parse_base_quote(reference_symbol)
        if parsed is None:
            continue
        base_asset, quote = parsed
        if base_asset in commons_constants.USD_LIKE_COINS:
            continue

        sticky_fetch_symbol = trading_api.get_daily_close_source(daily_prices, base_asset)
        if _is_daily_cache_up_to_date(daily_prices, reference_symbol):
            continue

        since_ms = _compute_fetch_since_ms(daily_prices, reference_symbol)
        candidates = _build_fetch_candidates(
            exchange_manager, base_asset, quote, sticky_fetch_symbol,
        )

        fetch_result = await _fetch_daily_candles(
            exchange_manager, since_ms, candidates,
        )
        if fetch_result is None:
            logger.info(
                "Skipping daily price fetch for %s on %s: no supported market found",
                reference_symbol,
                exchange_name,
            )
            continue

        candles, fetch_symbol, is_reversed = fetch_result
        if sticky_fetch_symbol and fetch_symbol != sticky_fetch_symbol:
            logger.info(
                "Migrating daily closes for %s on %s from %s to %s",
                base_asset,
                exchange_name,
                sticky_fetch_symbol,
                fetch_symbol,
            )
            await trading_api.rename_daily_closes_symbol(
                exchange_name, exchange_type, sandboxed,
                sticky_fetch_symbol, fetch_symbol, data_root,
            )
            trading_api.move_daily_prices_symbol_in_memory(
                daily_prices, sticky_fetch_symbol, fetch_symbol,
            )
        elif fetch_symbol != reference_symbol:
            logger.debug(
                "Fetched %s for %s on %s",
                fetch_symbol,
                reference_symbol,
                exchange_name,
            )

        closes_by_timestamp = _closes_from_candles(candles, is_reversed)
        closes_by_timestamp = _filter_closes_for_merge(
            daily_prices, fetch_symbol, closes_by_timestamp,
        )
        if not closes_by_timestamp:
            continue

        await trading_api.merge_daily_prices(
            exchange_name, exchange_type, sandboxed, fetch_symbol, closes_by_timestamp, data_root,
        )
        await trading_api.set_daily_close_source(
            exchange_name, exchange_type, sandboxed, base_asset, fetch_symbol, data_root,
        )
        trading_api.set_daily_close_source_in_memory(daily_prices, base_asset, fetch_symbol)
        trading_api.merge_daily_prices_in_memory(daily_prices, fetch_symbol, closes_by_timestamp)


def _parse_base_quote(symbol: str) -> tuple[str, str] | None:
    base_asset, quote = symbol_util.parse_symbol(symbol).base_and_quote()
    if not base_asset or not quote or base_asset == quote:
        return None
    return base_asset, quote


def _ordered_usd_like_quotes(quote: str) -> list[str]:
    quotes = []
    if "USD" in commons_constants.USD_LIKE_COINS and quote != "USD":
        quotes.append("USD")
    for usd_like_quote in commons_constants.USD_LIKE_COINS:
        if usd_like_quote == quote or usd_like_quote in quotes:
            continue
        quotes.append(usd_like_quote)
    return quotes


def _is_reversed_fetch_symbol(base_asset: str, fetch_symbol: str) -> bool:
    parsed = _parse_base_quote(fetch_symbol)
    if parsed is None:
        return False
    fetch_base, _fetch_quote = parsed
    return fetch_base != base_asset


def _build_fetch_candidates(
    exchange_manager,
    base_asset: str,
    quote: str,
    sticky_fetch_symbol: str | None,
) -> list[tuple[str, bool]]:
    candidates: list[tuple[str, bool]] = []
    seen_fetch_symbols: set[str] = set()

    def add_candidate(fetch_symbol: str | None, is_reversed: bool) -> None:
        if fetch_symbol is None or fetch_symbol in seen_fetch_symbols:
            return
        seen_fetch_symbols.add(fetch_symbol)
        candidates.append((fetch_symbol, is_reversed))

    if sticky_fetch_symbol:
        add_candidate(
            sticky_fetch_symbol,
            _is_reversed_fetch_symbol(base_asset, sticky_fetch_symbol),
        )

    direct_symbol, is_reversed = exchange_util.get_associated_symbol(
        exchange_manager, base_asset, quote,
    )
    add_candidate(direct_symbol, is_reversed)

    if quote in commons_constants.USD_LIKE_COINS:
        for alt_quote in _ordered_usd_like_quotes(quote):
            alt_symbol, alt_is_reversed = exchange_util.get_associated_symbol(
                exchange_manager, base_asset, alt_quote,
            )
            add_candidate(alt_symbol, alt_is_reversed)

    return candidates


async def _get_historical_daily_candles(
    exchange_manager,
    fetch_symbol: str,
    since_ms: int | None,
) -> list:
    start_time_ms, end_time_ms = _compute_fetch_time_range_ms(since_ms)
    candles = []
    async for batch in exchange_util.get_historical_ohlcv(
        exchange_manager,
        fetch_symbol,
        commons_enums.TimeFrames.ONE_DAY,
        start_time_ms,
        end_time_ms,
    ):
        candles.extend(batch)
    return candles


async def _get_symbol_daily_candles(
    exchange_manager,
    fetch_symbol: str,
    since_ms: int | None,
) -> list:
    fetch_kwargs = {}
    if since_ms is not None:
        fetch_kwargs["since"] = since_ms
    return await exchange_manager.exchange.get_symbol_prices(
        fetch_symbol,
        commons_enums.TimeFrames.ONE_DAY,
        **fetch_kwargs,
    )


def _supports_full_candle_history(exchange_name: str) -> bool:
    return exchange_name in trading_constants.FULL_CANDLE_HISTORY_EXCHANGES


async def _fetch_daily_candles(
    exchange_manager,
    since_ms: int | None,
    candidates: list[tuple[str, bool]],
) -> tuple[list, str, bool] | None:
    exchange_name = exchange_manager.exchange_name
    supports_full_history = _supports_full_candle_history(exchange_name)
    for fetch_symbol, is_reversed in candidates:
        if supports_full_history:
            candles = await _try_full_history_daily_candles(
                exchange_manager, exchange_name, fetch_symbol, since_ms,
            )
        else:
            candles = await _try_limited_history_daily_candles(
                exchange_manager, exchange_name, fetch_symbol, since_ms,
            )
        if candles:
            return candles, fetch_symbol, is_reversed
    return None


async def _try_full_history_daily_candles(
    exchange_manager,
    exchange_name: str,
    fetch_symbol: str,
    since_ms: int | None,
) -> list | None:
    try:
        candles = await _get_historical_daily_candles(
            exchange_manager, fetch_symbol, since_ms,
        )
    except trading_errors.UnSupportedSymbolError:
        return None
    except trading_errors.FailedRequest as error:
        logger.info(
            "Daily candle historical fetch failed for %s on %s, retrying with get_symbol_prices: %s",
            fetch_symbol,
            exchange_name,
            error,
        )
    else:
        if candles:
            return candles
        logger.info(
            "Daily candle historical fetch returned empty for %s on %s, retrying with get_symbol_prices",
            fetch_symbol,
            exchange_name,
        )

    try:
        return await _get_symbol_daily_candles(
            exchange_manager, fetch_symbol, since_ms,
        )
    except trading_errors.UnSupportedSymbolError:
        return None
    except trading_errors.FailedRequest as error:
        logger.exception(
            error,
            True,
            f"Failed to fetch daily candles for {fetch_symbol}: {error}",
        )
        return None


async def _try_limited_history_daily_candles(
    exchange_manager,
    exchange_name: str,
    fetch_symbol: str,
    since_ms: int | None,
) -> list | None:
    try:
        candles = await _get_symbol_daily_candles(
            exchange_manager, fetch_symbol, since_ms,
        )
    except trading_errors.UnSupportedSymbolError:
        return None
    except trading_errors.FailedRequest as error:
        if since_ms is not None:
            logger.info(
                "Daily candle incremental fetch failed for %s on %s, skipping fallback without since: %s",
                fetch_symbol,
                exchange_name,
                error,
            )
            return None
        logger.info(
            "Daily candle ideal fetch failed for %s on %s, retrying without since/limit: %s",
            fetch_symbol,
            exchange_name,
            error,
        )
        try:
            candles = await _get_symbol_daily_candles(
                exchange_manager, fetch_symbol, None,
            )
        except trading_errors.UnSupportedSymbolError:
            return None
        except trading_errors.FailedRequest as fallback_error:
            logger.error(
                "Failed to fetch daily candles for %s on %s after fallback without since/limit: %s",
                fetch_symbol,
                exchange_name,
                fallback_error,
            )
            return None
    if candles:
        return candles
    return None


def _closes_from_candles(candles: list, is_reversed: bool) -> dict[str, float]:
    closes_by_timestamp = {}
    for candle in candles:
        day_ts = str(int(candle[0]))
        close_price = float(candle[4])
        if is_reversed:
            close_price = 1.0 / close_price
        closes_by_timestamp[day_ts] = close_price
    return closes_by_timestamp


def _filter_closes_for_merge(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    fetch_symbol: str,
    closes_by_timestamp: dict[str, float],
) -> dict[str, float]:
    oldest_cached = trading_api.get_oldest_daily_price_timestamp(daily_prices, fetch_symbol)
    if oldest_cached is not None:
        oldest_cached_int = int(oldest_cached)
        return {
            day_ts: close
            for day_ts, close in closes_by_timestamp.items()
            if int(day_ts) >= oldest_cached_int
        }
    lookback_floor = _utc_day_start(time.time()) - (
        flow_constants.PORTFOLIO_HISTORY_DAILY_LOOKBACK_DAYS * commons_constants.DAYS_TO_SECONDS
    )
    lookback_floor_int = int(lookback_floor)
    return {
        day_ts: close
        for day_ts, close in closes_by_timestamp.items()
        if int(day_ts) >= lookback_floor_int
    }


def _utc_day_start(timestamp: float) -> float:
    """Return the UTC day-start (00:00:00) for the given unix timestamp."""
    return float(math.floor(
        timestamp / commons_constants.DAYS_TO_SECONDS
    ) * commons_constants.DAYS_TO_SECONDS)


def _compute_fetch_since_ms(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
) -> int | None:
    newest_timestamp = trading_api.get_latest_daily_price_timestamp(daily_prices, symbol)
    if newest_timestamp is None:
        return None

    since_seconds = newest_timestamp - commons_constants.DAYS_TO_SECONDS
    return int(since_seconds * 1000)


def _compute_fetch_time_range_ms(since_ms: int | None) -> tuple[int, int]:
    end_time_ms = int(time.time() * commons_constants.MSECONDS_TO_SECONDS)
    if since_ms is not None:
        return since_ms, end_time_ms
    lookback_ms = (
        flow_constants.PORTFOLIO_HISTORY_DAILY_LOOKBACK_DAYS
        * commons_constants.DAYS_TO_SECONDS
        * commons_constants.MSECONDS_TO_SECONDS
    )
    return end_time_ms - lookback_ms, end_time_ms


def _is_daily_cache_up_to_date(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
) -> bool:
    latest_cached_timestamp = trading_api.get_latest_daily_price_timestamp(daily_prices, symbol)
    if latest_cached_timestamp is None:
        return False
    return latest_cached_timestamp >= _utc_day_start(time.time())
