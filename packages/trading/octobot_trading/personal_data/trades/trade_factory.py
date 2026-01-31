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
import typing

import octobot_commons.logging as logging
import octobot_trading.personal_data.trades.trade as trade_class
import octobot_trading.personal_data.orders.order as order_class  # pylint: disable=unused-import
import octobot_trading.personal_data.orders.order_factory as order_factory
import octobot_trading.enums as enums
import octobot_trading.constants as constants


def create_trade_instance_from_raw(trader, raw_trade: dict[str, typing.Any]) -> "trade_class.Trade":
    order = create_closed_order_instance_from_raw_trade(trader, raw_trade)
    exchange_trade_id = raw_trade.get(enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value)
    return create_trade_from_order(order, exchange_trade_id=exchange_trade_id)


def create_closed_order_instance_from_raw_trade(trader, raw_trade: dict[str, typing.Any]) -> "order_class.Order":
    order = order_factory.create_order_from_raw(trader, raw_trade)
    order.update_from_raw(raw_trade)
    if order.status is enums.OrderStatus.CANCELED:
        # ensure order is considered canceled
        order.consider_as_canceled()
    else:
        # ensure order is considered filled
        order.consider_as_filled()
    return order


def create_trade_from_order(order: "order_class.Order",
                            close_status: typing.Optional[enums.OrderStatus] = None,
                            creation_time: int = 0,
                            canceled_time: int = 0,
                            executed_time: int = 0,
                            exchange_trade_id: typing.Optional[str] = None) -> "trade_class.Trade":
    if close_status is not None:
        order.status = close_status
    trade = trade_class.Trade(order.trader)
    trade.update_from_order(order,
                            canceled_time=canceled_time,
                            creation_time=creation_time,
                            executed_time=executed_time,
                            exchange_trade_id=exchange_trade_id)
    if trade.get_time() < constants.MINIMUM_VAL_TRADE_TIME:
        logging.get_logger("TradeFactory").error(f"Trade with invalid trade time ({trade.get_time()}) "
                                                 f"from order: {order}")
    return trade


def create_trade_from_dict(trader, trade_dict: dict[str, typing.Any]) -> "trade_class.Trade":
    return trade_class.Trade.from_dict(trader, trade_dict)
