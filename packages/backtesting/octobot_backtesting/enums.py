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
import enum 


class DataFormats(enum.Enum):
    REGULAR_COLLECTOR_DATA = 0


class DataFormatKeys(enum.Enum):
    SYMBOLS = "symbols"
    EXCHANGE = "exchange"
    DATE = "date"
    TIMESTAMP = "timestamp"
    START_TIMESTAMP = "start_timestamp"
    END_TIMESTAMP = "end_timestamp"
    START_DATE = "start_date"
    END_DATE = "end_date"
    CANDLES = "candles"
    CANDLES_LENGTH = "candles_length"
    TIME_FRAMES = "time_frames"
    TYPE = "type"
    VERSION = "version"


class ReportFormat(enum.Enum):
    SYMBOL_REPORT = "symbol_report"
    BOT_REPORT = "bot_report"
    SYMBOLS_WITH_TF = "symbols_with_time_frames_frames"


class DataTables(enum.Enum):
    DESCRIPTION = "description"


class ExchangeDataTables(enum.Enum):
    RECENT_TRADES = "recent_trades"
    ORDER_BOOK = "order_book"
    OHLCV = "ohlcv"
    KLINE = "kline"
    TICKER = "ticker"
    FUNDING = "funding"
