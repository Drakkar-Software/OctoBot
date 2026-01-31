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
import contextlib

import octobot_commons.logging as logging
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_trading.constants as constants
import octobot_trading.personal_data.orders.active_order_swap_strategies as active_order_swap_strategies


class OrderGroup:
    def __init__(
        self, name, orders_manager,
        active_order_swap_strategy: typing.Optional[active_order_swap_strategies.ActiveOrderSwapStrategy] = None
    ):
        self.name: str = name
        self.orders_manager = orders_manager
        self.active_order_swap_strategy: active_order_swap_strategies.ActiveOrderSwapStrategy = active_order_swap_strategy or self._default_active_order_swap_strategy(
            constants.ACTIVE_ORDER_STRATEGY_SWAP_TIMEOUT
        )
        self.logger: logging.BotLogger = logging.get_logger(str(self))
        self.enabled: bool = True

        self._lock: typing.Optional[asyncio_tools.RLock] = None

    async def on_fill(self, filled_order, ignored_orders=None):
        """
        Called when an order referencing this group is filled
        This is called right before updating portfolio for this filled order and the
        order fill publication
        :param filled_order: the filled order
        :param ignored_orders: orders that should be ignored
        """

    async def on_cancel(self, cancelled_order, ignored_orders=None):
        """
        Called when an order referencing this group is cancelled
        This is called before updating portfolio for this cancelled order and the
        order cancel publication
        :param cancelled_order: the cancelled order
        :param ignored_orders: orders that should be ignored
        """

    async def adapt_before_order_becoming_active(self, order_to_become_active) -> list:
        """
        Called before an order referencing this group is becoming active
        """

    @contextlib.asynccontextmanager
    async def lock_group(self):
        if self._lock is None:
            self._lock = asyncio_tools.RLock()
        async with self._lock:
            yield

    def _default_active_order_swap_strategy(self, timeout: float) -> active_order_swap_strategies.ActiveOrderSwapStrategy:
        """
        Called when an order of this group is becoming active
        """
        raise NotImplementedError("_default_active_order_swap_strategy is not implemented")


    async def enable(self, enabled):
        self.enabled = enabled

    def get_group_open_orders(self):
        return [
            order
            for order in (
                open_order
                for open_order in self.orders_manager.get_order_from_group(self.name)
                if open_order.is_open() and not (open_order.is_cancelling())
            )
            # when is_synchronization_enabled is disabled, orders' state might not be set and executed, also ensure
            # orders are not filled or closed
            if order.is_synchronization_enabled() or not (order.is_filled() or order.is_closed())
        ]

    def clear(self):
        self.orders_manager = None

    def __str__(self):
        return f"{self.__class__.__name__} #{self.name}"

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
               self.orders_manager is other.orders_manager \
               and self.name == other.name
