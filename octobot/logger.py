#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import logging
import os
import shutil
import traceback
import logging.config as config

import sys
import async_channel.channels as channel_instances
import async_channel.enums as channel_enums

import octobot_commons.enums as enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as common_logging
import octobot_commons.channels_name as channels_name
import octobot_commons.pretty_printer as pretty_printer

import octobot_evaluators.evaluators.channel as evaluator_channels

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums

import octobot.constants as constants
import octobot.configuration_manager as configuration_manager

BOT_CHANNEL_LOGGER = None
LOGGER_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.OPTIONAL.value


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception("".join(traceback.format_tb(tb)))
    logging.exception("{0}: {1}".format(ex_cls, ex))


def init_logger():
    try:
        if not os.path.exists(constants.LOGS_FOLDER):
            os.mkdir(constants.LOGS_FOLDER)
        _load_logger_config()
        init_bot_channel_logger()
    except KeyError:
        print(
            "Impossible to start OctoBot: the logging configuration can't be found in '"
            + constants.LOGGING_CONFIG_FILE
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


def init_bot_channel_logger():
    # overwrite BOT_CHANNEL_LOGGER to apply global logging configuration
    global BOT_CHANNEL_LOGGER
    BOT_CHANNEL_LOGGER = common_logging.get_logger("OctoBot Channel")


def _load_logger_config():
    try:
        # use local logging file to allow users to customize the log level
        if not os.path.isfile(configuration_manager.get_user_local_config_file()):
            if not os.path.exists(commons_constants.USER_FOLDER):
                os.mkdir(commons_constants.USER_FOLDER)
            shutil.copyfile(constants.LOGGING_CONFIG_FILE, configuration_manager.get_user_local_config_file())
        config.fileConfig(configuration_manager.get_user_local_config_file())
    except Exception as ex:
        config.fileConfig(constants.LOGGING_CONFIG_FILE)
        logging.getLogger("Logging Configuration").warning(f"Impossible to initialize local logging configuration file,"
                                                           f" using default one. {ex}")


async def init_exchange_chan_logger(exchange_id):
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.OHLCV_CHANNEL.value,
                                     exchange_id).new_consumer(
        ohlcv_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.BALANCE_CHANNEL.value,
                                     exchange_id).new_consumer(
        balance_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.TRADES_CHANNEL.value,
                                     exchange_id).new_consumer(
        trades_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.LIQUIDATIONS_CHANNEL.value,
                                     exchange_id).new_consumer(
        liquidations_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.POSITIONS_CHANNEL.value,
                                     exchange_id).new_consumer(
        positions_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    )
    await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.ORDERS_CHANNEL.value,
                                     exchange_id).new_consumer(
        orders_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    )
    # secondary logs, very verbose on websockets
    if constants.ENV_TRADING_ENABLE_DEBUG_LOGS:
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.RECENT_TRADES_CHANNEL.value,
                                         exchange_id).new_consumer(
            recent_trades_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.FUNDING_CHANNEL.value,
                                         exchange_id).new_consumer(
            funding_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.TICKER_CHANNEL.value,
                                         exchange_id).new_consumer(
            ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.MINI_TICKER_CHANNEL.value,
                                         exchange_id).new_consumer(
            mini_ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.ORDER_BOOK_CHANNEL.value,
                                         exchange_id).new_consumer(
            order_book_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.ORDER_BOOK_TICKER_CHANNEL.value,
                                         exchange_id).new_consumer(
            order_book_ticker_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.KLINE_CHANNEL.value,
                                         exchange_id).new_consumer(
            kline_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.MARK_PRICE_CHANNEL.value,
                                         exchange_id).new_consumer(
            mark_price_callback, priority_level=LOGGER_PRIORITY_LEVEL
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.BALANCE_PROFITABILITY_CHANNEL.value,
                                         exchange_id).new_consumer(
            balance_profitability_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
        )


async def init_evaluator_chan_logger(matrix_id: str):
    await evaluator_channels.get_chan(channels_name.OctoBotEvaluatorsChannelsName.MATRIX_CHANNEL.value,
                                      matrix_id).new_consumer(
        matrix_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )
    await evaluator_channels.get_chan(channels_name.OctoBotEvaluatorsChannelsName.EVALUATORS_CHANNEL.value,
                                      matrix_id).new_consumer(
        evaluators_callback, priority_level=LOGGER_PRIORITY_LEVEL
    )


async def init_octobot_chan_logger(bot_id: str):
    await channel_instances.get_chan_at_id(constants.OCTOBOT_CHANNEL, bot_id).new_consumer(
        octobot_channel_callback,
        priority_level=LOGGER_PRIORITY_LEVEL,
        bot_id=bot_id,
        subject=[enums.OctoBotChannelSubjects.NOTIFICATION.value, enums.OctoBotChannelSubjects.ERROR.value]
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
    BOT_CHANNEL_LOGGER.debug(
        f"MARK PRICE : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} "
        f"|| SYMBOL = {symbol} || MARK PRICE = {mark_price}"
    )


async def balance_callback(exchange: str, exchange_id: str, balance):
    BOT_CHANNEL_LOGGER.debug(f"BALANCE : EXCHANGE = {exchange} || BALANCE = {balance}")


async def balance_profitability_callback(
        exchange: str,
        exchange_id: str,
        profitability,
        profitability_percent,
        market_profitability_percent,
        initial_portfolio_current_profitability,
):
    BOT_CHANNEL_LOGGER.debug(
        f"BALANCE PROFITABILITY : EXCHANGE = {exchange} || PROFITABILITY = "
        f"{pretty_printer.portfolio_profitability_pretty_print(profitability, profitability_percent, 'USDT')}"
    )


async def trades_callback(
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        trade: dict,
        old_trade: bool,
):
    BOT_CHANNEL_LOGGER.debug(
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
        is_new: bool,
        is_from_bot: bool,
):
    order_string = f"ORDERS : EXCHANGE = {exchange} || SYMBOL = {symbol} || " \
                   f"{pretty_printer.open_order_pretty_printer(exchange, order)} || " \
                   f"status = {order.get(trading_enums.ExchangeConstantsOrderColumns.STATUS.value, None)} || " \
                   f"CREATED = {is_new} || FROM_BOT = {is_from_bot}"
    BOT_CHANNEL_LOGGER.debug(order_string)


async def positions_callback(
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        position,
        is_updated: bool
):
    BOT_CHANNEL_LOGGER.debug(f"POSITIONS : EXCHANGE = {exchange} || POSITIONS = {position}")


async def funding_callback(
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        funding_rate,
        predicted_funding_rate,
        next_funding_time,
        timestamp,
):
    BOT_CHANNEL_LOGGER.debug(
        f"FUNDING : EXCHANGE = {exchange} || CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
        f"|| RATE = {str(funding_rate)} || NEXT RATE = {str(predicted_funding_rate)}"
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
