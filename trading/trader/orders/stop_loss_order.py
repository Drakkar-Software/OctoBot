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
from config import TradeOrderSide, TraderOrderType, OrderStatus
from trading.trader.order import Order


class StopLossOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, last_prices: list, simulated_time=False):
        if self.check_last_prices(last_prices, self.origin_price, True, simulated_time):
            self.status = OrderStatus.FILLED
            self.filled_price = self.origin_price
            self.filled_quantity = self.origin_quantity
            self.total_cost = self.filled_price * self.filled_quantity
            self.executed_time = self.generate_executed_time(simulated_time)
            if self.trader.simulate:
                # compute normal fees
                self.fee = self.get_computed_fee()
            else:
                # force 0 fee: not a real order: only used as a trigger
                self.fee = self.get_computed_fee(forced_value=0)
                for order in self.linked_orders:
                    await self.trader.cancel_order(order)
                await self.trader.create_artificial_order(TraderOrderType.SELL_MARKET, self.symbol, self.origin_price,
                                                          self.origin_quantity, self.origin_price,
                                                          self.linked_portfolio)
