#  Drakkar-Software OctoBot-Trading
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

from octobot_trading.personal_data.trades import trades_manager
from octobot_trading.personal_data.trades import trade_factory
from octobot_trading.personal_data.trades import channel
from octobot_trading.personal_data.trades import trade

from octobot_trading.personal_data.trades.trades_manager import (
    TradesManager,
)
from octobot_trading.personal_data.trades.trade_factory import (
    create_trade_instance_from_raw,
    create_closed_order_instance_from_raw_trade,
    create_trade_from_order,
    create_trade_from_dict,
)
from octobot_trading.personal_data.trades.channel import (
    TradesProducer,
    TradesChannel,
    TradesUpdater,
)
from octobot_trading.personal_data.trades.trade import (
    Trade,
)
from octobot_trading.personal_data.trades.trade_pnl import (
    TradePnl,
)
from octobot_trading.personal_data.trades.trades_util import (
    compute_win_rate,
    aggregate_trades_by_exchange_order_id,
    get_real_or_estimated_trade_fee,
)

__all__ = [
    "TradesManager",
    "TradesProducer",
    "TradesChannel",
    "create_trade_instance_from_raw",
    "create_closed_order_instance_from_raw_trade",
    "create_trade_from_order",
    "create_trade_from_dict",
    "TradesUpdater",
    "Trade",
    "TradePnl",
    "compute_win_rate",
    "aggregate_trades_by_exchange_order_id",
    "get_real_or_estimated_trade_fee",
]
