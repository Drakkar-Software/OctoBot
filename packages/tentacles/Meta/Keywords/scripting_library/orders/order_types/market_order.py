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

import tentacles.Meta.Keywords.scripting_library.orders.order_types.create_order as create_order


async def market(
    context,
    side=None,
    symbol=None,

    amount=None,
    target_position=None,

    stop_loss_offset=None,
    stop_loss_tag=None,
    stop_loss_type=None,
    stop_loss_group=None,
    take_profit_offset=None,
    take_profit_tag=None,
    take_profit_type=None,
    take_profit_group=None,

    reduce_only=False,

    tag=None,

    group=None,
    wait_for=None
):
    return await create_order.create_order_instance(
        context,
        side=side,
        symbol=symbol or context.symbol,

        order_amount=amount,
        order_target_position=target_position,

        stop_loss_offset=stop_loss_offset,
        stop_loss_tag=stop_loss_tag,
        stop_loss_type=stop_loss_type,
        stop_loss_group=stop_loss_group,
        take_profit_offset=take_profit_offset,
        take_profit_tag=take_profit_tag,
        take_profit_type=take_profit_type,
        take_profit_group=take_profit_group,

        order_type_name="market",

        reduce_only=reduce_only,

        tag=tag,
        group=group,
        wait_for=wait_for
    )
