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
import tentacles.Meta.Keywords.scripting_library.orders.position_size as position_size
import octobot_trading.modes.script_keywords as script_keywords

async def scaled_limit(
        context,
        side=None,
        symbol=None,

        order_type_name="limit",

        scale_from=None,
        scale_to=None,
        order_count=10,
        distribution="linear",

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

        slippage_limit=None,
        time_limit=None,

        reduce_only=False,
        post_only=False,

        tag=None,

        group=None,
        wait_for=None
):
    amount_per_order = None
    unknown_portfolio_on_creation = wait_for is not None
    if target_position is None and amount is not None:
        amount_per_order = await position_size. \
            get_amount(context, amount, side=side, use_total_holding=True,
                       unknown_portfolio_on_creation=unknown_portfolio_on_creation) / order_count

    elif target_position is not None and amount is None and side is None:
        total_amount, side = await position_size.get_target_position(
            context, target_position, reduce_only=reduce_only,
            unknown_portfolio_on_creation=unknown_portfolio_on_creation)
        amount_per_order = total_amount / order_count
    else:
        raise RuntimeError("Either use side with amount or target_position for scaled orders.")

    scale_from_price = await script_keywords.get_price_with_offset(context, scale_from, side=side)
    scale_to_price = await script_keywords.get_price_with_offset(context, scale_to, side=side)
    order_prices = []
    if distribution == "linear":
        if scale_from_price >= scale_to_price:
            price_difference = scale_from_price - scale_to_price
            step_size = price_difference / (order_count - 1)
            for i in range(0, order_count):
                order_prices.append(scale_from_price - (step_size * i))
        elif scale_to_price > scale_from_price:
            price_difference = scale_to_price - scale_from_price
            step_size = price_difference / (order_count - 1)
            for i in range(0, order_count):
                order_prices.append(scale_from_price + (step_size * i))

    else:
        raise RuntimeError("scaled order: unsupported distribution type. check the documentation for more informations")
    created_orders = []
    for order_price in order_prices:
        new_created_order = await create_order.create_order_instance(
            context,
            side=side,
            symbol=symbol or context.symbol,

            order_amount=amount_per_order,

            order_type_name="limit",
            order_offset=f"@{order_price}",

            stop_loss_offset=stop_loss_offset,
            stop_loss_tag=stop_loss_tag,
            stop_loss_type=stop_loss_type,
            stop_loss_group=stop_loss_group,
            take_profit_offset=take_profit_offset,
            take_profit_tag=take_profit_tag,
            take_profit_type=take_profit_type,
            take_profit_group=take_profit_group,

            slippage_limit=slippage_limit,
            time_limit=time_limit,

            reduce_only=reduce_only,
            post_only=post_only,
            group=group,
            tag=tag,

            wait_for=wait_for
        )
        try:
            created_orders.append(new_created_order[0])
        except IndexError:
            pass
            # raise RuntimeError(f"scaled {side} order not created")
    return created_orders


async def scaled_stop_loss(
        context,
        side=None,
        symbol=None,

        scale_from=None,
        scale_to=None,
        order_count=10,
        distribution="linear",

        amount=None,
        target_position=None,

        slippage_limit=None,
        time_limit=None,

        tag=None,

        group=None,
        wait_for=None
):
    await scaled_limit(context,
                       side=side,
                       symbol=symbol,

                       order_type_name="stop_loss",

                       scale_from=scale_from,
                       scale_to=scale_to,
                       order_count=order_count,
                       distribution=distribution,

                       amount=amount,
                       target_position=target_position,

                       slippage_limit=slippage_limit,
                       time_limit=time_limit,

                       reduce_only=True,

                       tag=tag,

                       group=group,
                       wait_for=wait_for
                       )
