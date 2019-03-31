#  Drakkar-Software OctoBot
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

from backtesting import backtesting_enabled
from config import TimeFrames, PriceIndexes, PriceStrings, BOT_TOOLS_BACKTESTING, CONFIG_WILDCARD
from interfaces import get_bot, get_default_time_frame, get_global_config
from interfaces.web import add_to_symbol_data_history, \
    get_symbol_data_history
from tools.timestamp_util import convert_timestamps_to_datetime, convert_timestamp_to_datetime
from tools.time_frame_manager import TimeFrameManager
from interfaces.trading_util import get_trades_history
from interfaces.web.models.trading import get_exchange_time_frames

GET_SYMBOL_SEPARATOR = "|"


def parse_get_symbol(get_symbol):
    return get_symbol.replace(GET_SYMBOL_SEPARATOR, "/")


def get_value_from_dict_or_string(data, is_time_frame=False):
    if isinstance(data, dict):
        if is_time_frame:
            return TimeFrames(data["value"])
        else:
            return data["value"]
    else:
        if is_time_frame:
            if data is None:
                return get_default_time_frame()
            else:
                return TimeFrames(data)
        else:
            return data


def _format_trades(trade_history):
    trade_time_key = "time"
    trade_price_key = "price"
    trade_description_key = "trade_description"
    trade_order_side_key = "order_side"
    trades = {
        trade_time_key: [],
        trade_price_key: [],
        trade_description_key: [],
        trade_order_side_key: []
    }

    for trade in trade_history:
        trades[trade_time_key].append(convert_timestamp_to_datetime(trade.filled_time,
                                                                    time_format="%y-%m-%d %H:%M:%S"))
        trades[trade_price_key].append(trade.price)
        trades[trade_description_key].append(f"{trade.order_type.name}: {trade.quantity}")
        trades[trade_order_side_key].append(trade.side.value)

    return trades


def remove_invalid_chars(string):
    return string.split("[")[0]


def _get_candles_reply(exchange, symbol_evaluator, time_frame):
    return {
        "exchange": remove_invalid_chars(exchange.get_name()),
        "symbol": symbol_evaluator.get_symbol(),
        "time_frame": time_frame.value
    }


def get_watched_symbol_data(symbol):
    bot = get_bot()
    exchanges = bot.get_exchanges_list()
    symbol = parse_get_symbol(symbol)

    try:
        if exchanges:
            exchange = next(iter(exchanges.values()))
            evaluators = bot.get_symbol_evaluator_list()
            if evaluators and symbol in evaluators:
                symbol_evaluator = evaluators[symbol]
                time_frame = TimeFrameManager.get_display_time_frame(bot.get_config())
                return _get_candles_reply(exchange, symbol_evaluator, time_frame)
    except KeyError:
        return {}
    return {}


def _find_symbol_evaluator_with_data(evaluators, exchange):
    symbol_evaluator = next(iter(evaluators.values()))
    first_symbol = symbol_evaluator.get_symbol()
    exchange_traded_pairs = exchange.get_exchange_manager().get_traded_pairs()
    if first_symbol in exchange_traded_pairs:
        return symbol_evaluator
    elif first_symbol == CONFIG_WILDCARD:
        return evaluators[exchange_traded_pairs[0]]
    else:
        for symbol in evaluators.keys():
            if symbol in exchange_traded_pairs:
                return evaluators[symbol]
    return symbol_evaluator


def get_first_symbol_data():
    bot = get_bot()
    exchanges = bot.get_exchanges_list()

    try:
        if exchanges:
            exchange = next(iter(exchanges.values()))
            evaluators = bot.get_symbol_evaluator_list()
            if evaluators:
                symbol_evaluator = _find_symbol_evaluator_with_data(evaluators, exchange)
                time_frame = TimeFrameManager.get_display_time_frame(bot.get_config())
                return _get_candles_reply(exchange, symbol_evaluator, time_frame)
    except KeyError:
        return {}
    return {}


def create_candles_data(symbol, time_frame, new_data, bot, list_arrays, in_backtesting):
    candles_key = "candles"
    real_trades_key = "real_trades"
    simulated_trades_key = "simulated_trades"
    result_dict = {
        candles_key: [],
        real_trades_key: [],
        simulated_trades_key: [],
    }

    if not in_backtesting:
        add_to_symbol_data_history(symbol, new_data, time_frame, False)
        data = get_symbol_data_history(symbol, time_frame)
    else:
        data = new_data

    data_x = convert_timestamps_to_datetime(data[PriceIndexes.IND_PRICE_TIME.value],
                                            time_format="%y-%m-%d %H:%M:%S",
                                            force_timezone=False)

    real_trades_history, simulated_trades_history = get_trades_history(bot, symbol)

    if real_trades_history:
        result_dict[real_trades_key] = _format_trades(real_trades_history)

    if simulated_trades_history:
        result_dict[simulated_trades_key] = _format_trades(simulated_trades_history)

    if list_arrays:
        result_dict[candles_key] = {
            PriceStrings.STR_PRICE_TIME.value: data_x,
            PriceStrings.STR_PRICE_CLOSE.value: data[PriceIndexes.IND_PRICE_CLOSE.value].tolist(),
            PriceStrings.STR_PRICE_LOW.value: data[PriceIndexes.IND_PRICE_LOW.value].tolist(),
            PriceStrings.STR_PRICE_OPEN.value: data[PriceIndexes.IND_PRICE_OPEN.value].tolist(),
            PriceStrings.STR_PRICE_HIGH.value: data[PriceIndexes.IND_PRICE_HIGH.value].tolist(),
            PriceStrings.STR_PRICE_VOL.value: data[PriceIndexes.IND_PRICE_VOL.value].tolist()
        }
    else:
        result_dict[candles_key] = {
            PriceStrings.STR_PRICE_TIME.value: data_x,
            PriceStrings.STR_PRICE_CLOSE.value: data[PriceIndexes.IND_PRICE_CLOSE.value],
            PriceStrings.STR_PRICE_LOW.value: data[PriceIndexes.IND_PRICE_LOW.value],
            PriceStrings.STR_PRICE_OPEN.value: data[PriceIndexes.IND_PRICE_OPEN.value],
            PriceStrings.STR_PRICE_HIGH.value: data[PriceIndexes.IND_PRICE_HIGH.value]
        }
    return result_dict


def get_currency_price_graph_update(exchange_name, symbol, time_frame, list_arrays=True, backtesting=False):
    bot = get_bot()
    if backtesting and bot.get_tools() and bot.get_tools()[BOT_TOOLS_BACKTESTING]:
        bot = bot.get_tools()[BOT_TOOLS_BACKTESTING].get_bot()
    symbol = parse_get_symbol(symbol)
    symbol_evaluator_list = bot.get_symbol_evaluator_list()
    in_backtesting = backtesting_enabled(get_global_config()) or backtesting

    exchange = exchange_name
    exchange_list = bot.get_exchanges_list()
    if backtesting:
        exchanges = [key for key in exchange_list if exchange_name in key]
        if exchanges:
            exchange = exchanges[0]

    if time_frame is not None:
        if symbol_evaluator_list:
            evaluator_thread_managers = symbol_evaluator_list[symbol].get_evaluator_task_managers(
                exchange_list[exchange])

            data = None

            if time_frame in evaluator_thread_managers:
                if backtesting:
                    exchange_simulator = exchange_list[exchange].get_exchange()
                    data = exchange_simulator.get_full_candles_data(symbol, time_frame)
                else:
                    evaluator_thread_manager = evaluator_thread_managers[time_frame]
                    data = evaluator_thread_manager.get_evaluator().get_data()
            elif not backtesting and time_frame in get_exchange_time_frames(exchange_name)[0]:
                # might be the real-time evaluator time frame => check in symbol data
                data = get_bot().run_in_main_asyncio_loop(
                    exchange_list[exchange].get_symbol_prices(symbol, time_frame, return_list=False)
                )

            if data is not None:
                return create_candles_data(symbol, time_frame, data, bot, list_arrays, in_backtesting)
    return None
