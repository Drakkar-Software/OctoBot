#  Drakkar-Software OctoBot-Tentacles
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
import time
import typing
import datetime

import octobot_commons
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.profiles as commons_profiles
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.symbols
import octobot_commons.logging

import octobot_trading.exchanges
import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools

import octobot.community
import octobot.enums
import octobot.constants as constants

import tentacles.Meta.Keywords.scripting_library.errors as scr_errors
import tentacles.Meta.Keywords.scripting_library.configuration as scr_configuration
import tentacles.Meta.Keywords.scripting_library.exchanges as src_exchanges
import tentacles.Meta.Keywords.scripting_library.constants as scr_constants

import tentacles.Meta.Keywords.scripting_library.errors as errors


async def init_exchange_market_status_and_populate_backtesting_exchange_data(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
    backend_type: typing.Optional[octobot.enums.CommunityHistoricalBackendType] = None,
) -> exchange_data_import.ExchangeData:
    """
    Initializes the exchange market status and populates the backtesting exchange data.
    If a backend type is provided, it will use the historical client to populate the backtesting exchange data.
    Otherwise, it will use the ccxt exchange manager to populate the backtesting exchange data.
    """
    async with data_collector_ccxt_exchange_manager(
        profile_data, exchange_data
    ) as exchange_manager:
        if backend_type is not None:
            async with octobot.community.history_backend_client(
                backend_type=backend_type
            ) as historical_client:
                return await populate_backtesting_exchange_data_from_historical_client(
                    exchange_data, profile_data, historical_client, exchange_manager.exchange_name
                )
        return await fetch_and_populate_backtesting_exchange_data(
            exchange_data, profile_data, exchange_manager
        )


async def fetch_and_populate_backtesting_exchange_data(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
) -> exchange_data_import.ExchangeData:
    start_time, end_time, time_frames, symbols = _get_backtesting_run_details(profile_data)
    for time_frame in time_frames:
        await exchanges_test_tools.add_symbols_details(
            exchange_manager, symbols, time_frame.value, exchange_data,
            start_time=start_time, end_time=end_time,
            close_price_only=False,
            include_latest_candle=False,
        )
    first_candle_times = []
    for market in exchange_data.markets:
        first_candle_times.append(market.time[0])
    _ensure_start_time(exchange_data, start_time, first_candle_times)
    return exchange_data


def _get_backtesting_run_details(
    profile_data: commons_profiles.ProfileData,
) -> (float, float, list[common_enums.TimeFrames], list[str]):
    start_time = get_backtesting_start_time(profile_data)
    end_time = time.time()
    time_frames = [
        common_enums.TimeFrames(tf)
        for tf in scr_configuration.get_time_frames(profile_data, for_historical_data=True)
    ]
    if (
        scr_configuration.requires_price_update_timeframe(profile_data)
        and scr_constants.PRICE_UPDATE_TIME_FRAME.value not in time_frames
    ):
        time_frames.append(scr_constants.PRICE_UPDATE_TIME_FRAME)
    symbols = scr_configuration.get_traded_symbols(profile_data)
    return start_time, end_time, time_frames, symbols


def get_backtesting_start_time(
    profile_data: commons_profiles.ProfileData
) -> float:
    return time.time() - profile_data.backtesting_context.start_time_delta


def iter_fetched_ohlcvs(ohlcvs: list[list[typing.Union[float, str]]]):
    ohlcvs_by_symbol = {}
    for ohlcv in ohlcvs:
        time_frame = ohlcv[0]
        symbol = ohlcv[1]
        candles = ohlcv[2:]
        if symbol not in ohlcvs_by_symbol:
            ohlcvs_by_symbol[symbol] = {}
        if time_frame not in ohlcvs_by_symbol[symbol]:
            ohlcvs_by_symbol[symbol][time_frame] = []
        ohlcvs_by_symbol[symbol][time_frame].append(candles)
    for symbol, time_frames in ohlcvs_by_symbol.items():
        for time_frame, ohlcvs in time_frames.items():
            yield symbol, time_frame, ohlcvs


async def populate_backtesting_exchange_data_from_historical_client(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
    historical_client: octobot.community.HistoricalBackendClient,
    exchange_name: str
) -> exchange_data_import.ExchangeData:
    start_time, end_time, time_frames, symbols = _get_backtesting_run_details(profile_data)
    first_traded_symbols, last_traded_symbols, first_historical_config_time = (
        scr_configuration.get_oldest_historical_config_symbols_and_time(profile_data, start_time)
    )
    exchange_data.exchange_details.name = profile_data.backtesting_context.exchanges[0]   # todo handle multi exchanges
    scr_configuration.set_backtesting_portfolio(profile_data, exchange_data)
    exchange_data, updated_start_time = await update_backtesting_symbols_data(
        historical_client, profile_data, exchange_name, symbols, time_frames, exchange_data, start_time, end_time,
        first_traded_symbols, last_traded_symbols, first_historical_config_time
    )
    if not scr_configuration.can_convert_ref_market_to_usd_like(exchange_data, profile_data):
        # usd like convert
        try:
            usd_like_time_frame = time_frames[0]
            symbol = await find_usd_like_symbol_from_available_history(
                historical_client, exchange_data.exchange_details.name,
                profile_data.trading.reference_market, usd_like_time_frame, updated_start_time, end_time,
            )
            await update_backtesting_symbols_data(
                historical_client, profile_data, exchange_name, [symbol], [usd_like_time_frame],
                exchange_data, updated_start_time, end_time, [symbol], [symbol],
                first_historical_config_time, close_price_only=True,
            )
        except scr_errors.InvalidBacktestingDataError as err:
            # can't convert ref market into usd like value
            _get_logger().error(f"Can't convert ref market into usd like value: {err}")
        except KeyError as err:
            # can't convert ref market into usd like value
            _get_logger().error(
                f"Can't convert ref market into usd like value: missing {err} timeframe values"
            )
    return exchange_data


async def init_backtesting_exchange_market_status_cache(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
):
    async with data_collector_ccxt_exchange_manager(profile_data, exchange_data):
        # nothing to do, initializing the exchange manager is enough to fetch market statuses
        pass


@contextlib.asynccontextmanager
async def data_collector_ccxt_exchange_manager(
    profile_data: commons_profiles.ProfileData,
    exchange_data: exchange_data_import.ExchangeData,
):
    exchange_data.exchange_details.name = profile_data.backtesting_context.exchanges[0]
    tentacles_setup_config = scr_configuration.get_full_tentacles_setup_config()
    exchange_config_by_exchange = scr_configuration.get_config_by_tentacle(profile_data)
    async with src_exchanges.local_ccxt_exchange_manager(
        exchange_data, tentacles_setup_config,
        exchange_config_by_exchange=exchange_config_by_exchange,
    ) as exchange_manager:
        try:
            yield exchange_manager
        except Exception as err:
            _get_logger().exception(err)
            raise


async def fetch_candles_history_range(
    historical_client: octobot.community.HistoricalBackendClient,
    exchange: str, symbol: str, time_frame: common_enums.TimeFrames
) -> (float, float):
    return await historical_client.fetch_candles_history_range(exchange, symbol, time_frame)


async def find_usd_like_symbol_from_available_history(
    historical_client: octobot.community.HistoricalBackendClient,
    exchange_name: str, base: str, time_frame: common_enums.TimeFrames,
    first_open_time: float, last_open_time: float,
) -> str:
    for usd_like_coin in common_constants.USD_LIKE_COINS:
        symbol = octobot_commons.symbols.merge_currencies(base, usd_like_coin)
        first_candle_time, last_candle_time = await fetch_candles_history_range(
            # always use production db
            historical_client, exchange_name, symbol, time_frame
        )
        if not (last_candle_time and first_candle_time):
            continue
        try:
            ensure_compatible_candle_time(
                exchange_name, symbol, time_frame,
                first_open_time, last_open_time, first_candle_time, last_candle_time,
                True, True, True, first_open_time,
                False
            )
            # did not raise: symbol can be used
            return symbol
        except scr_errors.InvalidBacktestingDataError:
            # can't use this symbol, proceed to the next one
            continue
    raise scr_errors.InvalidBacktestingDataError(
        f"No USD-like up to date candles found to convert {base} into USD-like on {exchange_name} {time_frame.value} "
        f"for first_open_time={first_open_time} last_open_time={last_open_time}"
    )


async def update_backtesting_symbols_data(
    historical_client: octobot.community.HistoricalBackendClient,
    profile_data: commons_profiles.ProfileData,
    exchange_name: str, symbols: list, time_frames: list,
    exchange_data: exchange_data_import.ExchangeData,
    start_time: float, end_time: float,
    first_traded_symbols: list, last_traded_symbols: list, first_traded_symbols_time: float,
    close_price_only: bool = False,
    requires_traded_symbol_prices_at_all_time: bool = True,
) -> (exchange_data_import.ExchangeData, float):
    updated_start_times = []
    is_custom_strategy = octobot.community.models.is_custom_strategy_profile(profile_data)
    # can adapt backtesting start and end time on custom strategies that require symbol prices at all time
    allow_any_backtesting_start_and_end_time = is_custom_strategy and requires_traded_symbol_prices_at_all_time

    all_ohlcvs = await historical_client.fetch_extended_candles_history(
        exchange_name, symbols, time_frames, start_time, end_time
    )

    for symbol, str_time_frame, ohlcvs in iter_fetched_ohlcvs(all_ohlcvs):
        time_frame = common_enums.TimeFrames(str_time_frame)
        # do not take current incomplete candle into account
        last_open_time = end_time - common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
        # When symbol in is first_traded_symbols, it should be available from the start
        # EXCEPT for custom strategies that might require trading pairs that don't exist for long enough
        # (when compatible with trading mode).
        # Otherwise, when it is available doesn't really matter.
        # If it's not available from the start, adapt start time to start as early as possible,
        # latest being first_traded_symbols_time.
        required_from_the_start = symbol in first_traded_symbols and (
            requires_traded_symbol_prices_at_all_time or not is_custom_strategy
        )
        required_till_the_end = symbol in last_traded_symbols
        updated_start_time = ensure_ohlcv_validity(
            ohlcvs, exchange_name, symbol, time_frame, start_time, last_open_time,
            required_from_the_start, required_till_the_end, first_traded_symbols_time,
            allow_any_backtesting_start_and_end_time
        )
        if updated_start_time is not None:
            updated_start_times.append(updated_start_time)
        exchange_data.markets.append(exchange_data_import.MarketDetails(
            symbol=symbol,
            time_frame=time_frame.value,
            close=[ohlcv[common_enums.PriceIndexes.IND_PRICE_CLOSE.value] for ohlcv in ohlcvs],
            open=[ohlcv[common_enums.PriceIndexes.IND_PRICE_OPEN.value] for ohlcv in ohlcvs]
            if not close_price_only else [],
            high=[ohlcv[common_enums.PriceIndexes.IND_PRICE_HIGH.value] for ohlcv in ohlcvs]
            if not close_price_only else [],
            low=[ohlcv[common_enums.PriceIndexes.IND_PRICE_LOW.value] for ohlcv in ohlcvs]
            if not close_price_only else [],
            volume=[ohlcv[common_enums.PriceIndexes.IND_PRICE_VOL.value] for ohlcv in ohlcvs]
            if not close_price_only else [],
            time=[ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value] for ohlcv in ohlcvs],
        ))
    updated_start_time = _ensure_start_time(
        exchange_data, start_time, updated_start_times
    )
    return exchange_data, updated_start_time


def _ensure_start_time(
    exchange_data: exchange_data_import.ExchangeData, ideal_start_time: float, updated_start_times: list[float]
) -> float:
    updated_start_time = max(updated_start_times) if updated_start_times else ideal_start_time
    if updated_start_time != ideal_start_time:
        # start time changed: remove extra candles
        _get_logger().warning(
            f"Adapting backtesting start time according to data availability. "
            f"Updated start time: {timestamp_util.convert_timestamp_to_datetime(updated_start_time)}. "
            f"Initial start time: {timestamp_util.convert_timestamp_to_datetime(ideal_start_time)}"
        )
        adapt_exchange_data_for_updated_start_time(exchange_data, updated_start_time)
    return updated_start_time


def ensure_ohlcv_validity(
    ohlcvs: list, exchange: str, symbol: str, time_frame: common_enums.TimeFrames,
    start_time: float, last_open_time: float, required_from_the_start: bool, required_till_the_end: bool,
    first_traded_symbols_time: float, allow_any_backtesting_start_and_end_time: bool
) -> typing.Optional[float]:
    if not ohlcvs:
        raise errors.InvalidBacktestingDataError(f"No {symbol} {time_frame.value} {exchange} OHLCV data")
    # ensure history is going approximately to start_time
    first_candle_time = ohlcvs[0][common_enums.PriceIndexes.IND_PRICE_TIME.value]
    last_candle_time = ohlcvs[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value]
    return ensure_compatible_candle_time(
        exchange, symbol, time_frame, start_time, last_open_time, first_candle_time, last_candle_time,
        False, required_from_the_start, required_till_the_end, first_traded_symbols_time,
        allow_any_backtesting_start_and_end_time
    )


def adapt_exchange_data_for_updated_start_time(
    exchange_data: exchange_data_import.ExchangeData, first_candle_time: float
):
    _get_logger().info(f"Filtering out backtesting candles to start at {first_candle_time}")
    for market in exchange_data.markets:
        market.time = [
            candle_time
            for candle_time in market.time
            if candle_time >= first_candle_time
        ]
        market.close = market.close[-len(market.time):]
        market.open = market.open[-len(market.time):]
        market.high = market.high[-len(market.time):]
        market.low = market.low[-len(market.time):]
        market.volume = market.volume[-len(market.time):]


def ensure_compatible_candle_time(
    exchange: str, symbol: str, time_frame: common_enums.TimeFrames,
    first_open_time: float, last_open_time: float, first_candle_time: float, last_candle_time: float,
    allow_candles_beyond_range: bool, required_from_the_start: bool, required_till_the_end: bool,
    first_traded_symbols_time: float, allow_any_backtesting_start_and_end_time: bool
) -> typing.Optional[float]:
    adapted_start_time = None
    # ensure history is going approximately to first_open_time
    if not allow_candles_beyond_range:
        # first_candle_time starting before the first_open_time (more candles than required)
        if first_candle_time < first_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW:
            raise errors.InvalidBacktestingDataError(
                f"{symbol} {time_frame.value} {exchange} OHLCV data starts too early "
                f"({first_candle_time} vs {first_open_time})"
            )
    time_frame_seconds = common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
    if first_candle_time > first_open_time + time_frame_seconds:
        if required_from_the_start:
            max_allowed_delayed_start = first_traded_symbols_time + constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW
            # missing initial candles, align start time to the first candle time when possible
            if allow_any_backtesting_start_and_end_time or first_candle_time < max_allowed_delayed_start:
                adapted_start_time = first_candle_time 
                _get_logger().info(
                    f"{symbol} {time_frame.value} {exchange} OHLCV data starts too late "
                    f"({first_candle_time} vs {first_open_time}): this is acceptable, start time is adapted to "
                    f"{first_candle_time} (delta: {datetime.timedelta(seconds=first_candle_time - first_open_time)})"
                )
            else:
                raise errors.InvalidBacktestingDataError(
                    f"{symbol} {time_frame.value} {exchange} OHLCV data starts too late "
                    f"({first_candle_time} vs {first_open_time})"
                )
        else:
            _get_logger().info(
                f"{symbol} {time_frame.value} {exchange} OHLCV data starts too late "
                f"({first_candle_time} vs {first_open_time}): this is acceptable, this symbol is not required from "
                f"the start"
            )
    # ensure history is going approximately until last_open_time
    if not allow_candles_beyond_range:
        # last_open_time ending after the last_candle_time (more candles than required)
        if last_open_time < last_candle_time:
            raise errors.InvalidBacktestingDataError(
                f"{symbol} {time_frame.value} {exchange} OHLCV data ends too late ({last_open_time} vs {last_candle_time})"
            )

    if last_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW > last_candle_time:
        if required_till_the_end:
            raise errors.InvalidBacktestingDataError(
                f"{symbol} {time_frame.value} {exchange} OHLCV data ends too early ({last_candle_time} vs {last_open_time})"
            )
        else:
            _get_logger().info(
                f"{symbol} {time_frame.value} {exchange} OHLCV data ends too early "
                f"({last_candle_time} vs {last_open_time}): this is acceptable, this symbol is not required till "
                f"the end of the run"
            )
    if adapted_start_time is not None and not allow_any_backtesting_start_and_end_time:
        # ensure adapted_start_time is not reducing too much the global backtesting duration
        ideal_duration = last_open_time - first_open_time
        adapted_duration = last_candle_time - adapted_start_time
        if adapted_duration < ideal_duration * constants.BACKTESTING_MIN_DURATION_RATIO:
            raise errors.InvalidBacktestingDataError(
                f"{symbol} {time_frame.value} {exchange} OHLCV adapted backtesting start time starts too late resulting "
                f"in a {round(adapted_duration/common_constants.DAYS_TO_SECONDS, 1)} days backtesting duration "
                f"vs {round(ideal_duration/common_constants.DAYS_TO_SECONDS, 1)} ideal days. Min allowed is "
                f"{round(ideal_duration * constants.BACKTESTING_MIN_DURATION_RATIO / common_constants.DAYS_TO_SECONDS, 1)} days."
            )
    return adapted_start_time


def _get_logger():
    return octobot_commons.logging.get_logger("ScriptingBacktestingDataCollector")
