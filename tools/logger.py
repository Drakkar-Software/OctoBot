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
from octobot_channels.channels.channel import get_chan
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.pretty_printer import PrettyPrinter
from octobot_evaluators.channels import MATRIX_CHANNEL
from octobot_trading.constants import TICKER_CHANNEL, RECENT_TRADES_CHANNEL, ORDER_BOOK_CHANNEL, KLINE_CHANNEL, \
    OHLCV_CHANNEL, BALANCE_CHANNEL, BALANCE_PROFITABILITY_CHANNEL, TRADES_CHANNEL, POSITIONS_CHANNEL, ORDERS_CHANNEL, \
    MARK_PRICE_CHANNEL
from octobot_trading.channels.exchange_channel import get_chan as get_trading_chan

BOT_CHANNEL_LOGGER = get_logger("OctoBot Channel")


async def init_exchange_chan_logger(exchange_id):
    await get_trading_chan(TICKER_CHANNEL, exchange_id).new_consumer(ticker_callback)
    await get_trading_chan(RECENT_TRADES_CHANNEL, exchange_id).new_consumer(recent_trades_callback)
    await get_trading_chan(ORDER_BOOK_CHANNEL, exchange_id).new_consumer(order_book_callback)
    await get_trading_chan(KLINE_CHANNEL, exchange_id).new_consumer(kline_callback)
    await get_trading_chan(OHLCV_CHANNEL, exchange_id).new_consumer(ohlcv_callback)
    await get_trading_chan(BALANCE_CHANNEL, exchange_id).new_consumer(balance_callback)
    await get_trading_chan(BALANCE_PROFITABILITY_CHANNEL, exchange_id).new_consumer(balance_profitability_callback)
    await get_trading_chan(TRADES_CHANNEL, exchange_id).new_consumer(trades_callback)
    await get_trading_chan(POSITIONS_CHANNEL, exchange_id).new_consumer(positions_callback)
    await get_trading_chan(ORDERS_CHANNEL, exchange_id).new_consumer(orders_callback)
    await get_trading_chan(MARK_PRICE_CHANNEL, exchange_id).new_consumer(mark_price_callback)


async def init_evaluator_chan_logger():
    await get_chan(MATRIX_CHANNEL).new_consumer(matrix_callback)


async def ticker_callback(exchange: str, exchange_id: str, symbol: str, ticker):
    BOT_CHANNEL_LOGGER.debug(f"TICKER : EXCHANGE = {exchange} || SYMBOL = {symbol} || TICKER = {ticker}")


async def order_book_callback(exchange: str, exchange_id: str, symbol: str, asks, bids):
    BOT_CHANNEL_LOGGER.debug(
        f"ORDERBOOK : EXCHANGE = {exchange} || SYMBOL = {symbol} || ASKS = {asks} || BIDS = {bids}")


async def ohlcv_callback(exchange: str, exchange_id: str, symbol: str, time_frame, candle):
    BOT_CHANNEL_LOGGER.debug(
        f"OHLCV : EXCHANGE = {exchange} || SYMBOL = {symbol} || TIME FRAME = {time_frame} || CANDLE = {candle}")


async def recent_trades_callback(exchange: str, exchange_id: str, symbol: str, recent_trades):
    BOT_CHANNEL_LOGGER.debug(
        f"RECENT TRADE : EXCHANGE = {exchange} || SYMBOL = {symbol} || RECENT TRADE = {recent_trades}")


async def kline_callback(exchange: str, exchange_id: str, symbol: str, time_frame, kline):
    BOT_CHANNEL_LOGGER.debug(
        f"KLINE : EXCHANGE = {exchange} || SYMBOL = {symbol} || TIME FRAME = {time_frame} || KLINE = {kline}")


async def mark_price_callback(exchange: str, exchange_id: str, symbol: str, mark_price):
    BOT_CHANNEL_LOGGER.info(f"MARK PRICE : EXCHANGE = {exchange} || SYMBOL = {symbol} || MARK PRICE = {mark_price}")


async def balance_callback(exchange: str, exchange_id: str, balance):
    BOT_CHANNEL_LOGGER.info(f"BALANCE : EXCHANGE = {exchange} || BALANCE = {balance}")


async def balance_profitability_callback(exchange: str, exchange_id: str, profitability, profitability_percent,
                                         market_profitability_percent, initial_portfolio_current_profitability):
    BOT_CHANNEL_LOGGER.info(f"BALANCE PROFITABILITY : EXCHANGE = {exchange} || PROFITABILITY = "
                            f"{PrettyPrinter.portfolio_profitability_pretty_print(profitability, profitability_percent, 'USDT')}")


async def trades_callback(exchange: str, exchange_id: str, symbol: str, trade: dict, old_trade: bool):
    BOT_CHANNEL_LOGGER.info(f"TRADES : EXCHANGE = {exchange} || SYMBOL = {symbol} || TRADE = {trade} "
                            f"|| OLD_TRADE = {old_trade}")


async def orders_callback(exchange: str, exchange_id: str, symbol: str, order: dict, is_closed, is_updated, is_from_bot):
    order_string = f"ORDERS : EXCHANGE = {exchange} || SYMBOL = {symbol} ||"
    if is_closed:
        # order_string += PrettyPrinter.trade_pretty_printer(exchange, order)
        order_string += PrettyPrinter.open_order_pretty_printer(exchange, order)
    else:
        order_string += PrettyPrinter.open_order_pretty_printer(exchange, order)

    order_string += f"|| CLOSED = {is_closed} || UPDATED = {is_updated} || FROM_BOT = {is_from_bot}"
    BOT_CHANNEL_LOGGER.info(order_string)


async def positions_callback(exchange: str, exchange_id: str, symbol: str, position, is_closed, is_updated,
                             is_from_bot):
    BOT_CHANNEL_LOGGER.info(f"POSITIONS : EXCHANGE = {exchange} || SYMBOL = {symbol} || POSITIONS = {position}"
                            f"|| CLOSED = {is_closed} || UPDATED = {is_updated} || FROM_BOT = {is_from_bot}")


async def matrix_callback(matrix_id,
                          evaluator_name,
                          evaluator_type,
                          eval_note,
                          eval_note_type,
                          exchange_name,
                          cryptocurrency,
                          symbol,
                          time_frame):
    BOT_CHANNEL_LOGGER.debug(f"EXCHANGE = {exchange_name} || EVALUATOR = {evaluator_name} ||"
                             f" CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} || TF = {time_frame} || NOTE = {eval_note} [MATRIX id = {matrix_id}] ")
