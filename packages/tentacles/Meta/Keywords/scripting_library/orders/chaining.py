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
import octobot_trading.personal_data as personal_data


async def chain_order(base_order, chained_orders, update_with_triggering_order_fees=False) -> list:
    # order creation return a list by default, handle it here
    orders = []
    if isinstance(base_order, list):
        if not base_order:
            return orders
        base_order = base_order[0]
    if not isinstance(chained_orders, list):
        chained_orders = [chained_orders]
    for order in chained_orders:
        await order.set_as_chained_order(base_order, False, {}, update_with_triggering_order_fees)
        base_order.add_chained_order(order)
        if base_order.is_filled() and order.should_be_created():
            await personal_data.create_as_chained_order(order)
        orders.append(order)
    return orders
