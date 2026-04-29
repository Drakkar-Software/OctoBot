#  Drakkar-Software OctoBot-Commons
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


class OctoBotChannelsName(enum.Enum):
    """
    OctoBot-Evaluators channel names
    """

    OCTOBOT_CHANNEL = "OctoBot"


class OctoBotUserChannelsName(enum.Enum):
    """
    OctoBot-Backtesting channel names
    """

    USER_COMMANDS_CHANNEL = "UserCommands"


class OctoBotEvaluatorsChannelsName(enum.Enum):
    """
    OctoBot-Evaluators channel names
    """

    MATRIX_CHANNEL = "Matrix"
    EVALUATORS_CHANNEL = "Evaluators"


class OctoBotBacktestingChannelsName(enum.Enum):
    """
    OctoBot-Backtesting channel names
    """

    TIME_CHANNEL = "Time"


class OctoBotCommunityChannelsName(enum.Enum):
    """
    OctoBot community channel names
    """

    REMOTE_TRADING_SIGNALS_CHANNEL = "RemoteTradingSignals"


class OctoBotTradingChannelsName(enum.Enum):
    """
    OctoBot-Trading channel names
    """

    OHLCV_CHANNEL = "OHLCV"
    TICKER_CHANNEL = "Ticker"
    MINI_TICKER_CHANNEL = "MiniTicker"
    RECENT_TRADES_CHANNEL = "RecentTrade"
    ORDER_BOOK_CHANNEL = "OrderBook"
    ORDER_BOOK_TICKER_CHANNEL = "OrderBookTicker"
    KLINE_CHANNEL = "Kline"
    TRADES_CHANNEL = "Trades"
    LIQUIDATIONS_CHANNEL = "Liquidations"
    ORDERS_CHANNEL = "Orders"
    BALANCE_CHANNEL = "Balance"
    BALANCE_PROFITABILITY_CHANNEL = "BalanceProfitability"
    POSITIONS_CHANNEL = "Positions"
    MODE_CHANNEL = "Mode"
    MARK_PRICE_CHANNEL = "MarkPrice"
    FUNDING_CHANNEL = "Funding"
    MARKETS_CHANNEL = "Markets"
