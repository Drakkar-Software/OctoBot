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
import dataclasses
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.orders.cancel_policies.order_cancel_policy as order_cancel_policy_import


@dataclasses.dataclass
class ChainedOrderFillingPriceOrderCancelPolicy(order_cancel_policy_import.OrderCancelPolicy):
    """
    Will cancel the order if at least one of the chained orders filling price is reached.
    """

    def should_cancel(self, order) -> bool:
        if order.is_cleared():
            self.get_logger().error(
                f"Ignored cancel policy: order {str(order)} has been cleared"
            )
            return False
        if not order.chained_orders:
            self.get_logger().error(
                f"Ignored cancel policy: order {str(order)} has no chained orders"
            )
            return False
        current_price, up_to_date = order_util.get_potentially_outdated_price(
            order.trader.exchange_manager, order.symbol
        )
        if not up_to_date:
            self.get_logger().error(
                f"Ignored cancel policy: order {str(order)} mark price: {current_price} is outdated"
            )
            return False
        for chained_order in order.chained_orders:
            if chained_order.trigger_above and current_price > chained_order.get_filling_price():
                # this chained order price is reached
                return True
            if not chained_order.trigger_above and current_price < chained_order.get_filling_price():
                # this chained order price is reached
                return True
        # no chained order price is reached
        return False
