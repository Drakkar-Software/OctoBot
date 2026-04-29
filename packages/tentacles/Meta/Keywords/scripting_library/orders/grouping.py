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
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords


def create_one_cancels_the_other_group(context, group_identifier=None, orders=None) \
        -> trading_personal_data.OneCancelsTheOtherOrderGroup:
    """
    Should be used to create temporary groups binding localized orders, where this group can be
    created once and directly associated to each order
    """
    return _create_order_group(context, trading_personal_data.OneCancelsTheOtherOrderGroup, group_identifier, orders)


def get_or_create_one_cancels_the_other_group(
        context, orders=None, include_chained_orders=True,
        group_identifier=None) -> trading_personal_data.OneCancelsTheOtherOrderGroup:
    """
    Should be used to manage long lasting groups that are meant to be re-used
    First: looks for groups in orders
    Second: looks for groups named as group_identifier
    Third: creates a group named as group_identifier
    """
    if group := get_group_from_orders(orders, include_chained_orders=include_chained_orders):
        return group
    return _get_or_create_order_group(context, trading_personal_data.OneCancelsTheOtherOrderGroup, group_identifier)


def create_balanced_take_profit_and_stop_group(context, group_identifier=None, orders=None) \
        -> trading_personal_data.BalancedTakeProfitAndStopOrderGroup:
    """
    Should be used to create temporary groups binding localized orders, where this group can be
    created once and directly associated to each order
    """
    return _create_order_group(context, trading_personal_data.BalancedTakeProfitAndStopOrderGroup,
                               group_identifier, orders)


def get_or_create_balanced_take_profit_and_stop_group(
        context, orders=None, include_chained_orders=True,
        group_identifier=None) -> trading_personal_data.BalancedTakeProfitAndStopOrderGroup:
    """
    Should be used to manage long lasting groups that are meant to be re-used
    First: looks for groups in orders
    Second: looks for groups named as group_identifier
    Third: creates a group named as group_identifier
    """
    if group := get_group_from_orders(orders, include_chained_orders=include_chained_orders):
        return group
    return _get_or_create_order_group(context, trading_personal_data.BalancedTakeProfitAndStopOrderGroup,
                                      group_identifier)


def add_orders_to_group(ctx, order_group, orders):
    orders = orders if isinstance(orders, list) else [orders]
    for order in orders:
        order.add_to_order_group(order_group)
        if basic_keywords.is_emitting_trading_signals(ctx):
            ctx.get_signal_builder().add_order_to_group(order, ctx.exchange_manager)


def get_group_from_orders(orders, include_chained_orders=True):
    if orders is None:
        return None
    orders = orders if isinstance(orders, list) else [orders]
    for order in orders:
        if order.order_group is not None:
            return order.order_group
        if include_chained_orders:
            if group := get_group_from_orders(order.chained_orders):
                return group
    return None


def get_open_orders_from_group(order_group):
    return order_group.get_group_open_orders()


async def enable_group(order_group, enabled):
    await order_group.enable(enabled)


def _create_order_group(context, group_type, group_identifier, orders) -> trading_personal_data.OrderGroup:
    group = context.exchange_manager.exchange_personal_data.orders_manager.create_group(group_type, group_identifier)
    if orders is not None:
        add_orders_to_group(context, group, orders)
    return group


def _get_or_create_order_group(context, group_type, group_identifier) -> trading_personal_data.OrderGroup:
    return context.exchange_manager.exchange_personal_data.orders_manager.get_or_create_group(group_type,
                                                                                              group_identifier)

