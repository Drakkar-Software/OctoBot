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
import octobot_trading.personal_data.orders.active_order_swap_strategies.active_order_swap_strategy as active_order_swap_strategy
import octobot_trading.enums as enums

_STOP_ORDER_TYPES = (
    enums.TraderOrderType.TRAILING_STOP, enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.STOP_LOSS_LIMIT
)

class StopFirstActiveOrderSwapStrategy(active_order_swap_strategy.ActiveOrderSwapStrategy):
    """
    Consider stop orders as priority orders
    """

    def is_priority_order(self, order) -> bool:
        return order.order_type in _STOP_ORDER_TYPES

