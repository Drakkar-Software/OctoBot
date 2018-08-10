from backtesting.backtesting import Backtesting
from config.cst import TimeFrames, PriceIndexes, PriceStrings, BOT_TOOLS_BACKTESTING
from interfaces import get_bot, get_default_time_frame, get_global_config
from interfaces.web import add_to_symbol_data_history, \
    get_symbol_data_history
from tools.symbol_util import split_symbol
from tools.timestamp_util import convert_timestamps_to_datetime

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


def get_currency_price_graph_update(exchange_name, symbol, time_frame, list_arrays=True, backtesting=False):
    bot = get_bot()
    if backtesting and bot.get_tools() and bot.get_tools()[BOT_TOOLS_BACKTESTING]:
        bot = bot.get_tools()[BOT_TOOLS_BACKTESTING].get_bot()
    symbol = parse_get_symbol(symbol)
    symbol_evaluator_list = bot.get_symbol_evaluator_list()
    in_backtesting = Backtesting.enabled(get_global_config()) or backtesting

    exchange = exchange_name
    exchange_list = bot.get_exchanges_list()
    if backtesting:
        exchanges = [key for key in exchange_list if exchange_name in key]
        if exchanges:
            exchange = exchanges[0]

    if time_frame is not None:
        if symbol_evaluator_list:
            evaluator_thread_managers = symbol_evaluator_list[symbol].get_evaluator_thread_managers(
                exchange_list[exchange])

            if time_frame in evaluator_thread_managers:
                evaluator_thread_manager = evaluator_thread_managers[time_frame]
                data = evaluator_thread_manager.get_evaluator().get_data()

                if data is not None:
                    _, pair_tag = split_symbol(symbol)
                    add_to_symbol_data_history(symbol, data, time_frame, in_backtesting)
                    data = get_symbol_data_history(symbol, time_frame)

                    data_x = convert_timestamps_to_datetime(data[PriceIndexes.IND_PRICE_TIME.value],
                                                            format="%y-%m-%d %H:%M:%S",
                                                            force_timezone=True)

                    if list_arrays:
                        return {
                            PriceStrings.STR_PRICE_TIME.value: data_x,
                            PriceStrings.STR_PRICE_CLOSE.value: data[PriceIndexes.IND_PRICE_CLOSE.value].tolist(),
                            PriceStrings.STR_PRICE_LOW.value: data[PriceIndexes.IND_PRICE_LOW.value].tolist(),
                            PriceStrings.STR_PRICE_OPEN.value: data[PriceIndexes.IND_PRICE_OPEN.value].tolist(),
                            PriceStrings.STR_PRICE_HIGH.value: data[PriceIndexes.IND_PRICE_HIGH.value].tolist()
                        }
                    else:
                        return {
                            PriceStrings.STR_PRICE_TIME.value: data_x,
                            PriceStrings.STR_PRICE_CLOSE.value: data[PriceIndexes.IND_PRICE_CLOSE.value],
                            PriceStrings.STR_PRICE_LOW.value: data[PriceIndexes.IND_PRICE_LOW.value],
                            PriceStrings.STR_PRICE_OPEN.value: data[PriceIndexes.IND_PRICE_OPEN.value],
                            PriceStrings.STR_PRICE_HIGH.value: data[PriceIndexes.IND_PRICE_HIGH.value]
                        }
    return None
