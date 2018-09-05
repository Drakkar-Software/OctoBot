from backtesting.backtesting import Backtesting
from config.cst import TimeFrames, PriceIndexes, PriceStrings, BOT_TOOLS_BACKTESTING
from interfaces import get_bot, get_default_time_frame, get_global_config
from interfaces.web import add_to_symbol_data_history, \
    get_symbol_data_history
from tools.symbol_util import split_symbol
from tools.timestamp_util import convert_timestamps_to_datetime, convert_timestamp_to_datetime
from interfaces.trading_util import get_trades_history

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

    for trades_per_trader in trade_history:
        for trade in trades_per_trader:
            trades[trade_time_key].append(convert_timestamp_to_datetime(trade.get_filled_time(),
                                                                        time_format="%y-%m-%d %H:%M:%S"))
            trades[trade_price_key].append(trade.get_price())
            trades[trade_description_key].append(f"{trade.get_order_type().name}: {trade.get_quantity()}")
            trades[trade_order_side_key].append(trade.get_side().value)

    return trades


def get_first_symbol_data():
    bot = get_bot()
    exchanges = bot.get_exchanges_list()

    try:
        if exchanges:
            exchange = next(iter(exchanges.values()))
            evaluators = bot.get_symbol_evaluator_list()
            if evaluators:
                symbol_evaluator = next(iter(evaluators.values()))
                etms = symbol_evaluator.get_evaluator_thread_managers(exchange)
                if etms:
                    time_frame = next(iter(etms))
                    return {
                        "exchange": exchange.get_name(),
                        "symbol": symbol_evaluator.get_symbol(),
                        "time_frame": time_frame.value
                    }
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

    if real_trades_history:
        result_dict[simulated_trades_key] = _format_trades(simulated_trades_history)

    if list_arrays:
        result_dict[candles_key] = {
            PriceStrings.STR_PRICE_TIME.value: data_x,
            PriceStrings.STR_PRICE_CLOSE.value: data[PriceIndexes.IND_PRICE_CLOSE.value].tolist(),
            PriceStrings.STR_PRICE_LOW.value: data[PriceIndexes.IND_PRICE_LOW.value].tolist(),
            PriceStrings.STR_PRICE_OPEN.value: data[PriceIndexes.IND_PRICE_OPEN.value].tolist(),
            PriceStrings.STR_PRICE_HIGH.value: data[PriceIndexes.IND_PRICE_HIGH.value].tolist()
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
                    return create_candles_data(symbol, time_frame, data, bot, list_arrays, in_backtesting)
    return None
