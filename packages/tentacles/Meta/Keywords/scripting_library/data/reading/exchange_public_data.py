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
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_trading.api as api
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_data
import octobot_trading.personal_data as personal_data
import octobot_trading.exchange_data as exchange_data
import octobot_trading.enums as trading_enums
import octobot_backtesting.api as backtesting_api
from octobot_trading.modes.script_keywords.basic_keywords import run_persistence as run_persistence
from tentacles.Evaluator.Util.candles_util import CandlesUtil


# real time in live mode
# lowest available candle time on backtesting
def current_live_time(context) -> float:
    return api.get_exchange_current_time(context.exchange_manager)


def symbol_fees(context, symbol=None) -> dict:
    return context.exchange_manager.exchange.get_fees(symbol or context.symbol)


def is_futures_trading(context) -> bool:
    return context.exchange_manager.is_future


def _time_frame_to_sec(context, time_frame=None):
    return commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame or context.time_frame)] * \
            commons_constants.MINUTE_TO_SECONDS


async def current_candle_time(context, symbol=None, time_frame=None, use_close_time=False):
    symbol = symbol or context.symbol
    time_frame = time_frame or context.time_frame
    candles_manager = api.get_symbol_candles_manager(
        api.get_symbol_data(context.exchange_manager, symbol, allow_creation=False), time_frame
    )
    if use_close_time:
        return candles_manager.time_candles[candles_manager.time_candles_index - 1] + \
               _time_frame_to_sec(context, time_frame)
    return candles_manager.time_candles[candles_manager.time_candles_index - 1]


async def current_closed_candle_time(context, symbol=None, time_frame=None):
    return await current_candle_time(context, symbol=symbol, time_frame=time_frame) \
        - _time_frame_to_sec(context, time_frame)


# Use capital letters to avoid python native lib conflicts
async def Time(context, symbol=None, time_frame=None, limit=-1, max_history=False, use_close_time=True):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if max_history and isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager):
        time_data = candles_manager.time_candles
    else:
        time_data = candles_manager.get_symbol_time_candles(-1 if max_history else limit)
    if use_close_time:
        return [value + _time_frame_to_sec(context, time_frame) for value in time_data]
    return time_data


# real time in live mode
# lowest available candle closes on backtesting
async def current_live_price(context, symbol=None):
    return await personal_data.get_up_to_date_price(context.exchange_manager, symbol or context.symbol,
                                                    timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                    base_error="Can't get the current price:")


async def current_candle_price(context, symbol=None, time_frame=None):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, False)
    return candles_manager.get_symbol_close_candles(1)[-1]


# Use capital letters to avoid python native lib conflicts
async def Open(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager) and max_history:
        return candles_manager.open_candles
    return candles_manager.get_symbol_open_candles(-1 if max_history else limit)


# Use capital letters to avoid python native lib conflicts
async def High(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager) and max_history:
        return candles_manager.high_candles
    return candles_manager.get_symbol_high_candles(-1 if max_history else limit)


# Use capital letters to avoid python native lib conflicts
async def Low(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager) and max_history:
        return candles_manager.low_candles
    return candles_manager.get_symbol_low_candles(-1 if max_history else limit)


# Use capital letters to avoid python native lib conflicts
async def Close(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager) and max_history:
        return candles_manager.close_candles
    return candles_manager.get_symbol_close_candles(-1 if max_history else limit)


async def hl2(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    try:
        from tentacles.Evaluator.Util.candles_util import CandlesUtil
        candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
        return CandlesUtil.HL2(
            candles_manager.get_symbol_high_candles(-1 if max_history else limit),
            candles_manager.get_symbol_low_candles(-1 if max_history else limit)
        )
    except ImportError:
        raise RuntimeError("CandlesUtil tentacle is required to use HL2")


async def hlc3(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    try:
        from tentacles.Evaluator.Util.candles_util import CandlesUtil
        candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
        return CandlesUtil.HLC3(
            candles_manager.get_symbol_high_candles(-1 if max_history else limit),
            candles_manager.get_symbol_low_candles(-1 if max_history else limit),
            candles_manager.get_symbol_close_candles(-1 if max_history else limit)
        )
    except ImportError:
        raise RuntimeError("CandlesUtil tentacle is required to use HLC3")


async def ohlc4(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    try:
        from tentacles.Evaluator.Util.candles_util import CandlesUtil
        candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
        return CandlesUtil.OHLC4(
            candles_manager.get_symbol_open_candles(-1 if max_history else limit),
            candles_manager.get_symbol_high_candles(-1 if max_history else limit),
            candles_manager.get_symbol_low_candles(-1 if max_history else limit),
            candles_manager.get_symbol_close_candles(-1 if max_history else limit)
        )
    except ImportError:
        raise RuntimeError("CandlesUtil tentacle is required to use OHLC4")


# Use capital letters to avoid python native lib conflicts
async def Volume(context, symbol=None, time_frame=None, limit=-1, max_history=False):
    candles_manager = await _get_candle_manager(context, symbol, time_frame, max_history)
    if isinstance(candles_manager, octobot_trading.exchange_data.PreloadedCandlesManager) and max_history:
        return candles_manager.close_candles
    return candles_manager.get_symbol_volume_candles(-1 if max_history else limit)


async def get_candles_from_name(ctx, source_name="low", time_frame=None, symbol=None, limit=-1, max_history=False):
    """
    source_name can be:
    "open", "high", "low", "close", "hl2", "hlc3", "ohlc4", "volume",
    "Heikin Ashi close", "Heikin Ashi open", "Heikin Ashi high", "Heikin Ashi low"
    """
    symbol = symbol or ctx.symbol
    time_frame = time_frame or ctx.time_frame
    if source_name == "close":
        return await Close(ctx, symbol, time_frame, limit, max_history)
    if source_name == "open":
        return await Open(ctx, symbol, time_frame, limit, max_history)
    if source_name == "high":
        return await High(ctx, symbol, time_frame, limit, max_history)
    if source_name == "low":
        return await Low(ctx, symbol, time_frame, limit, max_history)
    if source_name == "volume":
        return await Volume(ctx, symbol, time_frame, limit, max_history)
    if source_name == "time":
        return await Time(ctx, symbol, time_frame, limit, max_history)
    if source_name == "hl2":
        return await hl2(ctx, symbol, time_frame, limit, max_history)
    if source_name == "hlc3":
        return await hlc3(ctx, symbol, time_frame, limit, max_history)
    if source_name == "ohlc4":
        return await ohlc4(ctx, symbol, time_frame, limit, max_history)
    if "Heikin Ashi" in source_name:
        haOpen, haHigh, haLow, haClose = CandlesUtil.HeikinAshi(await Open(ctx, symbol, time_frame, limit, max_history),
                                                                await High(ctx, symbol, time_frame, limit, max_history),
                                                                await Low(ctx, symbol, time_frame, limit, max_history),
                                                                await Close(ctx, symbol, time_frame, limit, max_history)
                                                                )
        if source_name == "Heikin Ashi close":
            return haClose
        if source_name == "Heikin Ashi open":
            return haOpen
        if source_name == "Heikin Ashi high":
            return haHigh
        if source_name == "Heikin Ashi low":
            return haLow


async def _local_candles_manager(exchange_manager, symbol, time_frame, start_timestamp, end_timestamp):
    # warning: should only be called with an exchange simulator (in backtesting)
    ohlcv_data: list = await exchange_manager.exchange.exchange_importers[0].get_ohlcv(
        exchange_name=exchange_manager.exchange_name,
        symbol=symbol,
        time_frame=commons_enums.TimeFrames(time_frame))
    chronological_candles = sorted(ohlcv_data, key=lambda candle: candle[0])
    full_candles_history = [
        ohlcv[-1]
        for ohlcv in chronological_candles
        if start_timestamp <= ohlcv[0] <= end_timestamp
    ]
    candles_manager = exchange_data.CandlesManager(max_candles_count=len(full_candles_history))
    await candles_manager.initialize()
    candles_manager.replace_all_candles(full_candles_history)
    return candles_manager


async def _get_candle_manager(context, symbol, time_frame, max_history):
    symbol = symbol or context.symbol
    time_frame = time_frame or context.time_frame
    candle_manager = api.get_symbol_candles_manager(
        api.get_symbol_data(context.exchange_manager, symbol, allow_creation=False), time_frame
    )
    if max_history and context.exchange_manager.is_backtesting:
        if isinstance(candle_manager, octobot_trading.exchange_data.PreloadedCandlesManager):
            return candle_manager
        start_timestamp = backtesting_api.get_backtesting_starting_time(context.exchange_manager.exchange.backtesting)
        end_timestamp = backtesting_api.get_backtesting_ending_time(context.exchange_manager.exchange.backtesting)
        _key = symbol + time_frame + str(start_timestamp) + str(end_timestamp)
        try:
            return run_persistence.get_shared_element(_key)
        except KeyError:
            run_persistence.set_shared_element(
                _key,
                await _local_candles_manager(
                    context.exchange_manager, symbol, time_frame, start_timestamp, end_timestamp
                )
            )
            return run_persistence.get_shared_element(_key)
    return candle_manager


def get_digits_adapted_price(context, price, truncate=True):
    symbol_market = context.exchange_manager.exchange.get_market_status(context.symbol, with_fixer=False)
    return personal_data.decimal_adapt_price(symbol_market, price, truncate=truncate)


def get_digits_adapted_amount(context, amount, truncate=True):
    symbol_market = context.exchange_manager.exchange.get_market_status(context.symbol, with_fixer=False)
    return personal_data.decimal_adapt_quantity(symbol_market, amount, truncate=truncate)
