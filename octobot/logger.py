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
import logging
import os
import traceback
from logging.config import fileConfig

import sys
from octobot_channels.channels.channel_instances import get_chan_at_id

from octobot.constants import LOGGING_CONFIG_FILE, LOGS_FOLDER, OCTOBOT_CHANNEL
from octobot_commons.enums import OctoBotChannelSubjects, ChannelConsumerPriorityLevels
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.pretty_printer import (
    open_order_pretty_printer,
    portfolio_profitability_pretty_print,
)
from octobot_evaluators.channels.evaluator_channel import get_chan as get_evaluator_chan
from octobot_evaluators.constants import MATRIX_CHANNEL, EVALUATORS_CHANNEL
from octobot_trading.channels.exchange_channel import get_chan as get_trading_chan
from octobot_trading.constants import (
    TICKER_CHANNEL,
    RECENT_TRADES_CHANNEL,
    ORDER_BOOK_CHANNEL,
    KLINE_CHANNEL,
    OHLCV_CHANNEL,
    BALANCE_CHANNEL,
    BALANCE_PROFITABILITY_CHANNEL,
    TRADES_CHANNEL,
    POSITIONS_CHANNEL,
    ORDERS_CHANNEL,
    MARK_PRICE_CHANNEL,
    FUNDING_CHANNEL,
    LIQUIDATIONS_CHANNEL,
    MINI_TICKER_CHANNEL,
    ORDER_BOOK_TICKER_CHANNEL,
)

BOT_CHANNEL_LOGGER = None
LOGGER_PRIORITY_LEVEL = ChannelConsumerPriorityLevels.OPTIONAL.value


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception("".join(traceback.format_tb(tb)))
    logging.exception("{0}: {1}".format(ex_cls, ex))


def init_logger():
    try:
        if not os.path.exists(LOGS_FOLDER):
            os.mkdir(LOGS_FOLDER)

        fileConfig(LOGGING_CONFIG_FILE)
        # overwrite BOT_CHANNEL_LOGGER to apply global logging configuration
        global BOT_CHANNEL_LOGGER
        BOT_CHANNEL_LOGGER = get_logger("OctoBot Channel")
    except KeyError:
        print(
            "Impossible to start OctoBot: the logging configuration can't be found in '"
            + LOGGING_CONFIG_FILE
            + "' please make sure you are running OctoBot from its root directory."
        )
        os._exit(-1)

    logger = logging.getLogger("OctoBot Launcher")

    try:
        # Force new log file creation not to log at the previous one's end.
        logger.parent.handlers[1].doRollover()
    except PermissionError:
        print(
            "Impossible to start OctoBot: the logging file is locked, this is probably due to another running "
            "OctoBot instance."
        )
        os._exit(-1)

    sys.excepthook = _log_uncaught_exceptions
    return logger


async def init_exchange_chan_logger(exchange_id):
    await get_trading_chan(TICKER_CHANNEL, exchange_id).new_consumer(
        ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(MINI_TICKER_CHANNEL, exchange_id).new_consumer(
        mini_ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(RECENT_TRADES_CHANNEL, exchange_id).new_consumer(
        recent_trades_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(ORDER_BOOK_CHANNEL, exchange_id).new_consumer(
        order_book_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(ORDER_BOOK_TICKER_CHANNEL, exchange_id).new_consumer(
        order_book_ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(KLINE_CHANNEL, exchange_id).new_consumer(
        kline_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(OHLCV_CHANNEL, exchange_id).new_consumer(
        ohlcv_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(BALANCE_CHANNEL, exchange_id).new_consumer(
        balance_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(BALANCE_PROFITABILITY_CHANNEL, exchange_id).new_consumer(
        balance_profitability_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(TRADES_CHANNEL, exchange_id).new_consumer(
        trades_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(LIQUIDATIONS_CHANNEL, exchange_id).new_consumer(
        liquidations_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(POSITIONS_CHANNEL, exchange_id).new_consumer(
        positions_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(ORDERS_CHANNEL, exchange_id).new_consumer(
        orders_callback, priority_level=ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await get_trading_chan(MARK_PRICE_CHANNEL, exchange_id).new_consumer(
        mark_price_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_trading_chan(FUNDING_CHANNEL, exchange_id).new_consumer(
        funding_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )


async def init_evaluator_chan_logger(matrix_id: str):
    await get_evaluator_chan(MATRIX_CHANNEL, matrix_id).new_consumer(
        matrix_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await get_evaluator_chan(EVALUATORS_CHANNEL, matrix_id).new_consumer(
        evaluators_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )


async def init_octobot_chan_logger(bot_id: str):
    await get_chan_at_id(OCTOBOT_CHANNEL, bot_id).new_consumer(
        octobot_channel_callback,
        priority_level=LOGGER_PRIORITY_LEVEL,
        bot_id=bot_id,
        subject=[OctoBotChannelSubjects.NOTIFICATION.value, OctoBotChannelSubjects.ERROR.value]
    )


async def ticker_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, ticker
):
    BOT_CHANNEL_LOGGER.debug(
        f"TICKER : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || TICKER = {ticker}"
    )


async def mini_ticker_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mini_ticker
):
    BOT_CHANNEL_LOGGER.debug(
        f"MINI TICKER : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || MINI TICKER = {mini_ticker}"
    )


async def order_book_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, asks, bids
):
    BOT_CHANNEL_LOGGER.debug(
        f"ORDERBOOK : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || ASKS = {len(asks)} orders || BIDS = {len(bids)} orders"
    )


async def order_book_ticker_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    ask_quantity,
    ask_price,
    bid_quantity,
    bid_price,
):
    BOT_CHANNEL_LOGGER.debug(
        f"ORDERBOOK TICKER : EXCHANGE = {exchange} || SYMBOL = {symbol} "
        f"|| ASK PRICE / QUANTIY = {ask_price} / {ask_quantity}"
        f"|| BID PRICE / QUANTIY = {bid_price} / {bid_quantity}"
    )


async def ohlcv_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    time_frame,
    candle,
):
    BOT_CHANNEL_LOGGER.debug(
        f"OHLCV : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
        f"|| TIME FRAME = {time_frame} || CANDLE = {candle}"
    )


async def recent_trades_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, recent_trades
):
    BOT_CHANNEL_LOGGER.debug(
        f"RECENT TRADES : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || 10 first RECENT TRADES = {recent_trades[:10]}"
    )


async def liquidations_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, liquidations
):
    BOT_CHANNEL_LOGGER.debug(
        f"LIQUIDATIONS : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || LIQUIDATIONS = {liquidations}"
    )


async def kline_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, time_frame, kline
):
    BOT_CHANNEL_LOGGER.debug(
        f"KLINE : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
        f"|| TIME FRAME = {time_frame} || KLINE = {kline}"
    )


async def mark_price_callback(
    exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
):
    BOT_CHANNEL_LOGGER.info(
        f"MARK PRICE : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || MARK PRICE = {mark_price}"
    )


async def balance_callback(exchange: str, exchange_id: str, balance):
    BOT_CHANNEL_LOGGER.info(f"BALANCE : EXCHANGE = {exchange} || BALANCE = {balance}")


async def balance_profitability_callback(
    exchange: str,
    exchange_id: str,
    profitability,
    profitability_percent,
    market_profitability_percent,
    initial_portfolio_current_profitability,
):
    BOT_CHANNEL_LOGGER.info(
        f"BALANCE PROFITABILITY : EXCHANGE = {exchange} || PROFITABILITY = "
        f"{portfolio_profitability_pretty_print(profitability, profitability_percent, 'USDT')}"
    )


async def trades_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    trade: dict,
    old_trade: bool,
):
    BOT_CHANNEL_LOGGER.info(
        f"TRADES : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
        f"|| TRADE = {trade} "
        f"|| OLD_TRADE = {old_trade}"
    )


async def orders_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    order: dict,
    is_closed: bool,
    is_updated: bool,
    is_from_bot: bool,
):
    order_string = f"ORDERS : EXCHANGE = {exchange} || SYMBOL = {symbol} || "
    if is_closed:
        # order_string += PrettyPrinter.trade_pretty_printer(exchange, order)
        order_string += open_order_pretty_printer(exchange, order)
    else:
        order_string += open_order_pretty_printer(exchange, order)

    order_string += (
        f" || CLOSED = {is_closed} || UPDATED = {is_updated} || FROM_BOT = {is_from_bot}"
    )
    BOT_CHANNEL_LOGGER.info(order_string)


async def positions_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    position,
    is_closed: bool,
    is_updated: bool,
    is_liquidated: bool,
    is_from_bot: bool,
):
    BOT_CHANNEL_LOGGER.info(
        f"POSITIONS : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || POSITIONS = {position}"
        f"|| CLOSED = {is_closed} || UPDATED = {is_updated} || LIQUIDATED = {is_liquidated} "
        f"|| FROM_BOT = {is_from_bot}"
    )


async def funding_callback(
    exchange: str,
    exchange_id: str,
    cryptocurrency: str,
    symbol: str,
    funding_rate,
    next_funding_time,
    timestamp,
):
    BOT_CHANNEL_LOGGER.info(
        f"FUNDING : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
        f"|| RATE = {str(funding_rate)}"
        f"|| NEXT TIME = {str(next_funding_time)} || TIMESTAMP = {str(timestamp)}"
    )


async def matrix_callback(
    matrix_id,
    evaluator_name,
    evaluator_type,
    eval_note,
    eval_note_type,
    exchange_name,
    cryptocurrency,
    symbol,
    time_frame,
):
    BOT_CHANNEL_LOGGER.debug(
        f"MATRIX : EXCHANGE = {exchange_name} || "
        f"EVALUATOR = {evaluator_name} || EVALUATOR_TYPE = {evaluator_type} || "
        f"CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} || TF = {time_frame} "
        f"|| NOTE = {eval_note} [MATRIX id = {matrix_id}] "
    )


async def evaluators_callback(
    matrix_id,
    evaluator_name,
    evaluator_type,
    exchange_name,
    cryptocurrency,
    symbol,
    time_frame,
    data,
):
    BOT_CHANNEL_LOGGER.debug(
        f"EVALUATORS : EXCHANGE = {exchange_name} || "
        f"EVALUATOR = {evaluator_name} || EVALUATOR_TYPE = {evaluator_type} || "
        f"CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} || TF = {time_frame} "
        f"|| DATA = {data} [MATRIX id = {matrix_id}] "
    )


async def octobot_channel_callback(
        bot_id: str,
        subject: str,
        action: str,
        data: dict
):
    BOT_CHANNEL_LOGGER.debug(
        f"OCTOBOT_CHANNEL : SUBJECT = {subject} || ACTION = {action} || DATA = {data} "
    )
