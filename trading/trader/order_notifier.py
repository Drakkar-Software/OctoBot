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

from tools.notifications import OrdersNotification

"""
This class is used to perform order linked notification
"""


class OrderNotifier:
    def __init__(self, config, order):
        self.config = config
        self.order = order
        self.notifier = OrdersNotification(self.config)
        self.evaluator_notification = None

    async def notify(self, evaluator_notification):
        self.evaluator_notification = evaluator_notification
        orders = [order for order in self.order.get_linked_orders()]
        orders.append(self.order)
        await self.notifier.notify_create(evaluator_notification, orders)

    async def end(self,
                  order_filled,
                  orders_canceled,
                  trade_profitability,
                  portfolio_profitability,
                  portfolio_diff,
                  profitability=False):
        await self.notifier.notify_end(order_filled,
                                       orders_canceled,
                                       trade_profitability,
                                       portfolio_profitability,
                                       portfolio_diff,
                                       profitability)

    def set_order(self, order):
        self.order = order
