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
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.types.trailing.trailing_stop_order as trailing_stop_order


class TrailingStopLimitOrder(trailing_stop_order.TrailingStopOrder):
    UNINITIALIZED_LIMIT_PRICE = -1

    def __init__(self, trader, side=enums.TradeOrderSide.SELL, limit_price=UNINITIALIZED_LIMIT_PRICE):
        super().__init__(trader, side)
        self.order_type = enums.TraderOrderType.TRAILING_STOP_LIMIT
        self.limit_price = limit_price

    async def on_filled(self, enable_associated_orders_creation, force_artificial_orders=False):
        await trailing_stop_order.TrailingStopOrder.on_filled(
            self, enable_associated_orders_creation, force_artificial_orders=force_artificial_orders
        )
        order_type = (
            enums.TraderOrderType.SELL_LIMIT
            if self.side is enums.TradeOrderSide.SELL else enums.TraderOrderType.BUY_LIMIT
        )
        limit_price = (
            self.limit_price
            if self.limit_price != self.UNINITIALIZED_LIMIT_PRICE else self.origin_stop_price
        )
        self.on_filled_artificial_order = await self.trader.create_artificial_order(
            order_type, self.symbol, self.origin_stop_price, self.origin_quantity, limit_price,
            self.reduce_only, self.close_position
        )
