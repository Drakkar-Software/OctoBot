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
import octobot_trading.personal_data.orders.cancel_policies.order_cancel_policy as order_cancel_policy_import


@dataclasses.dataclass
class ExpirationTimeOrderCancelPolicy(order_cancel_policy_import.OrderCancelPolicy):
    """
    Will cancel the order if the expiration time is reached.
    """
    expiration_time: float

    def should_cancel(self, order) -> bool:
        if order.is_cleared():
            self.get_logger().error(
                f"Ignored cancel policy: order {str(order)} has been cleared"
            )
            return False
        return self.expiration_time <= order.trader.exchange_manager.exchange.get_exchange_current_time()
