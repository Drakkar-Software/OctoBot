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
import octobot_trading.personal_data.orders.types.limit.limit_order as limit_order


class TakeProfitOrder(limit_order.LimitOrder):
    def __init__(self, trader, side=enums.TradeOrderSide.SELL):
        super().__init__(trader, side)
        self.trigger_above = self.side is enums.TradeOrderSide.SELL

    async def update_price_if_outdated(self):
        pass

    def _filled_maker_or_taker(self):
        # Creates a market order when filled, which is taker
        return enums.ExchangeConstantsMarketPropertyColumns.TAKER.value

    async def on_filled(self, enable_associated_orders_creation, force_artificial_orders=False):
        await limit_order.LimitOrder.on_filled(
            self, enable_associated_orders_creation, force_artificial_orders=force_artificial_orders
        )
        if not self.trader.simulate and (self.is_self_managed() or force_artificial_orders):
            order_type = (
                enums.TraderOrderType.SELL_MARKET
                if self.side is enums.TradeOrderSide.SELL else enums.TraderOrderType.BUY_MARKET
            )
            self.on_filled_artificial_order = await self.trader.create_artificial_order(
                order_type, self.symbol, self.origin_stop_price, self.origin_quantity, self.origin_stop_price,
                self.reduce_only, self.close_position
            )
