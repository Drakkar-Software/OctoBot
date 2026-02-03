#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import time

import tentacles.Meta.Keywords.scripting_library.orders.open_orders as open_orders
import octobot_trading.personal_data as personal_data
import octobot_commons.logging as logging


async def wait_for_orders_close(ctx, orders, timeout=None):
    if not isinstance(orders, list):
        orders = [orders]
    t0 = time.time()
    refresh_interval = 0.01
    # wait for orders to be filled or cancelled
    # also wait for associated chained orders to be opened
    try:  # order.is_closed() fails when order got filled meanwhile
        while not all(order.is_closed() for order in orders) or \
                not are_all_chained_orders_created(ctx, orders):
            if timeout is None or time.time() - t0 < timeout:
                if ctx.exchange_manager.is_backtesting:
                    raise asyncio.TimeoutError("Can't wait for orders in backtesting")
                await asyncio.sleep(refresh_interval)
            else:
                raise asyncio.TimeoutError("Order wasnt not filled in time")
    except AttributeError as e:
        logging.get_logger("Waiting").exception(e, True, "AttributeError on checking orders (should not happen)")
        pass  # continue try to create take profit in case of connection issues


def are_all_chained_orders_created(ctx, orders):
    for order in orders:
        for chained_order in order.chained_orders:
            if not chained_order.is_created():
                return False
            if chained_order.is_closed():
                continue
            found_order = False
            # ensure that chained orders are open or got closed
            for open_order in open_orders.get_open_orders(ctx):
                if personal_data.is_associated_pending_order(open_order, chained_order):
                    found_order = True
                    break
            if not found_order:
                return False
    return True


async def wait_for_stop_loss_open(ctx, order_tag=None, order_group=None, timeout=60):
    """
    waits for and finds a stop order based on order tag or order group
    :param ctx:
    :param order_tag:
    :param order_group:
    :param timeout: in seconds
    :return: the stop loss order
    """
    t0 = time.time()
    refresh_interval = 0.01
    orders = ctx.exchange_manager.exchange_personal_data.orders_manager.orders

    stop_found = False
    while not stop_found:
        for order in orders:
            stop_found = orders[order].tag == order_tag or orders[order].order_group == order_group
            if stop_found:
                return orders[order]
        if timeout is None or time.time() - t0 < timeout:
            if ctx.exchange_manager.is_backtesting:
                raise asyncio.TimeoutError("Can't wait for orders in backtesting")
            await asyncio.sleep(refresh_interval)
        else:
            ctx.logger.error("Stop Loss Order was not found: was not placed in time or got already triggered")
            return None
