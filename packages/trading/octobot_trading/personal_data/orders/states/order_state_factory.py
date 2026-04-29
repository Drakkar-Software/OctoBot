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
import octobot_trading.constants as constants


async def create_order_state(
    order, is_from_exchange_data=False, enable_associated_orders_creation=True, 
    is_already_counted_in_available_funds=False, ignore_states=None
):
    if ignore_states is None:
        ignore_states = []

    if order.status is enums.OrderStatus.PENDING_CREATION \
       and enums.States.PENDING_CREATION not in ignore_states:
        await order.on_pending_creation(
            enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
    elif order.status is enums.OrderStatus.OPEN and enums.States.OPEN not in ignore_states:
        await order.on_open(
            force_open=False, is_from_exchange_data=is_from_exchange_data,
            enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
    elif order.status in constants.FILL_ORDER_STATUS_SCOPE \
            and enums.OrderStates.FILLED not in ignore_states \
            and enums.States.CLOSED not in ignore_states:
        await order.on_fill(
            force_fill=False, is_from_exchange_data=is_from_exchange_data,
            enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
    elif order.status in constants.CANCEL_ORDER_STATUS_SCOPE and enums.OrderStates.CANCELED not in ignore_states:
        await order.on_cancel(
            force_cancel=False, is_from_exchange_data=is_from_exchange_data,
            enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
