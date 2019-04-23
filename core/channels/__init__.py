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
from core.channels.exchange.ohlcv import OHLCVChannel
from core.channels.exchange.order_book import OrderBookChannel
from core.channels.exchange.recent_trade import RecentTradeChannel
from core.channels.exchange.ticker import TickerChannel

# General channels
# TODO

# Exchange channels
TICKER_CHANNEL = TickerChannel.get_name()
RECENT_TRADES_CHANNEL = RecentTradeChannel.get_name()
ORDER_BOOK_CHANNEL = OrderBookChannel.get_name()
OHLCV_CHANNEL = OHLCVChannel.get_name()
