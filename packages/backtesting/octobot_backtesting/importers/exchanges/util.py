#  Drakkar-Software OctoBot-Backtesting
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
import json

import octobot_commons.enums as commons_enums


def get_operations_from_timestamps(superior_timestamp, inferior_timestamp):
    operations: list = []
    timestamps: list = []
    if superior_timestamp != -1:
        timestamps.append(str(superior_timestamp))
        operations.append(commons_enums.DataBaseOperations.INF_EQUALS.value)
    if inferior_timestamp != -1:
        timestamps.append(str(inferior_timestamp))
        operations.append(commons_enums.DataBaseOperations.SUP_EQUALS.value)

    return timestamps, operations


def import_ohlcvs(ohlcvs):
    for i, val in enumerate(ohlcvs):
        ohlcvs[i] = list(val)
        ohlcvs[i][-1] = json.loads(ohlcvs[i][-1])
    return ohlcvs


def import_tickers(tickers):
    for ticker in tickers:
        ticker[-1] = json.loads(ticker[-1])
    return tickers


def import_order_books(order_books):
    for order_book in order_books:
        order_book[-1] = json.loads(order_book[-1])
        order_book[-2] = json.loads(order_book[-2])
    return order_books


def import_recent_trades(recent_trades):
    for recent_trade in recent_trades:
        recent_trade[-1] = json.loads(recent_trade[-1])
    return recent_trades


def import_klines(klines):
    for kline in klines:
        kline[-1] = json.loads(kline[-1])
    return klines
