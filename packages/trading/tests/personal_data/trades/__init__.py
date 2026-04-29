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
import octobot_trading.personal_data as personal_data
import octobot_trading.enums


def create_trade(trader, exchange_order_id, is_closing_order, origin_order_id):
    trade = personal_data.Trade(trader)
    trade.exchange_order_id = exchange_order_id
    trade.is_closing_order = is_closing_order
    trade.origin_order_id = origin_order_id
    return trade


def create_executed_trade(trader, side, executed_time, executed_quantity, executed_price, symbol, fee):
    trade = personal_data.Trade(trader)
    trade.executed_time = executed_time
    trade.executed_quantity = executed_quantity
    trade.executed_price = executed_price
    trade.symbol = symbol
    trade.fee = fee
    trade.side = side
    trade.trade_type = octobot_trading.enums.TraderOrderType.BUY_LIMIT
    trade.exchange_trade_type = octobot_trading.enums.TradeOrderType.LIMIT
    return trade
