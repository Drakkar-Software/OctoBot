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

from octobot_channels.channels import get_chan
from octobot_commons.pretty_printer import PrettyPrinter
from octobot_evaluators.channels import MATRIX_CHANNEL
from octobot_trading.channels import TICKER_CHANNEL, RECENT_TRADES_CHANNEL, ORDER_BOOK_CHANNEL, KLINE_CHANNEL, \
    OHLCV_CHANNEL, BALANCE_CHANNEL, BALANCE_PROFITABILITY_CHANNEL, TRADES_CHANNEL, POSITIONS_CHANNEL, ORDERS_CHANNEL
from octobot_trading.channels.exchange_channel import get_chan as get_trading_chan


async def init_exchange_chan_logger(exchange_name):
    await get_trading_chan(TICKER_CHANNEL, exchange_name).new_consumer(ticker_callback)
    await get_trading_chan(RECENT_TRADES_CHANNEL, exchange_name).new_consumer(recent_trades_callback)
    await get_trading_chan(ORDER_BOOK_CHANNEL, exchange_name).new_consumer(order_book_callback)
    await get_trading_chan(KLINE_CHANNEL, exchange_name).new_consumer(kline_callback)
    await get_trading_chan(OHLCV_CHANNEL, exchange_name).new_consumer(ohlcv_callback)
    await get_trading_chan(BALANCE_CHANNEL, exchange_name).new_consumer(balance_callback)
    await get_trading_chan(BALANCE_PROFITABILITY_CHANNEL, exchange_name).new_consumer(balance_profitability_callback)
    await get_trading_chan(TRADES_CHANNEL, exchange_name).new_consumer(trades_callback)
    await get_trading_chan(POSITIONS_CHANNEL, exchange_name).new_consumer(positions_callback)
    await get_trading_chan(ORDERS_CHANNEL, exchange_name).new_consumer(orders_callback)


async def init_evaluator_chan_logger():
    await get_chan(MATRIX_CHANNEL).new_consumer(matrix_callback)


async def ticker_callback(exchange, symbol, ticker):
    logging.info(f"TICKER : EXCHANGE = {exchange} || SYMBOL = {symbol} || TICKER = {ticker}")


async def order_book_callback(exchange, symbol, asks, bids):
    logging.info(f"ORDERBOOK : EXCHANGE = {exchange} || SYMBOL = {symbol} || ASKS = {asks} || BIDS = {bids}")


async def ohlcv_callback(exchange, symbol, time_frame, candle):
    logging.info(
        f"OHLCV : EXCHANGE = {exchange} || SYMBOL = {symbol} || TIME FRAME = {time_frame} || CANDLE = {candle}")


async def recent_trades_callback(exchange, symbol, recent_trades):
    logging.info(f"RECENT TRADE : EXCHANGE = {exchange} || SYMBOL = {symbol} || RECENT TRADE = {recent_trades}")


async def kline_callback(exchange, symbol, time_frame, kline):
    logging.info(
        f"KLINE : EXCHANGE = {exchange} || SYMBOL = {symbol} || TIME FRAME = {time_frame} || KLINE = {kline}")


async def balance_callback(exchange, balance):
    logging.info(f"BALANCE : EXCHANGE = {exchange} || BALANCE = {balance}")


async def balance_profitability_callback(exchange, profitability, profitability_percent, market_profitability_percent,
                                         initial_portfolio_current_profitability):
    logging.info(f"BALANCE PROFITABILITY : EXCHANGE = {exchange} || PROFITABILITY = "
                  f"{PrettyPrinter.portfolio_profitability_pretty_print(profitability, profitability_percent, 'USDT')}")


async def trades_callback(exchange, symbol, trade):
    logging.info(f"TRADES : EXCHANGE = {exchange} || SYMBOL = {symbol} || TRADE = {trade}")


async def orders_callback(exchange, symbol, order, is_closed, is_updated, is_from_bot):
    order_string = f"ORDERS : EXCHANGE = {exchange} || SYMBOL = {symbol} ||"
    if is_closed:
        # order_string += PrettyPrinter.trade_pretty_printer(exchange, order)
        order_string += PrettyPrinter.open_order_pretty_printer(exchange, order)
    else:
        order_string += PrettyPrinter.open_order_pretty_printer(exchange, order)

    order_string += f"|| CLOSED = {is_closed} || UPDATED = {is_updated} || FROM_BOT = {is_from_bot}"
    logging.info(order_string)


async def positions_callback(exchange, symbol, position, is_closed, is_updated, is_from_bot):
    logging.info(f"POSITIONS : EXCHANGE = {exchange} || SYMBOL = {symbol} || POSITIONS = {position}"
                  f"|| CLOSED = {is_closed} || UPDATED = {is_updated} || FROM_BOT = {is_from_bot}")


async def matrix_callback(evaluator_name,
                          evaluator_type,
                          eval_note,
                          exchange_name,
                          symbol,
                          time_frame):
    logging.info(f"MATRIX : EXCHANGE = {exchange_name} || EVALUATOR = {evaluator_name} ||"
                  f" SYMBOL = {symbol} || TF = {time_frame} || NOTE = {eval_note}")
