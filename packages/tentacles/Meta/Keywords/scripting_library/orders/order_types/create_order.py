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

import octobot_trading.personal_data as trading_personal_data
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.script_keywords as script_keywords
import tentacles.Meta.Keywords.scripting_library.settings as settings
import tentacles.Meta.Keywords.scripting_library.orders.position_size as position_size
import tentacles.Meta.Keywords.scripting_library.orders.chaining as chaining
import tentacles.Meta.Keywords.scripting_library.orders.grouping as grouping
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_private_data as exchange_private_data


async def create_order_instance(
    context,
    side=None,
    symbol=None,

    order_amount=None,
    order_target_position=None,

    stop_loss_offset=None,
    stop_loss_tag=None,
    stop_loss_type=None,
    stop_loss_group=False,
    take_profit_offset=None,
    take_profit_tag=None,
    take_profit_type=None,
    take_profit_group=False,

    order_type_name=None,

    order_offset=None,
    order_min_offset=None,
    order_max_offset=None,
    order_limit_offset=None,  # todo

    slippage_limit=None,
    time_limit=None,

    reduce_only=False,
    post_only=False,  # Todo
    tag=None,

    group=None,
    wait_for=None
):
    if not context.enable_trading or _paired_order_is_closed(context, group):
        return []
    async with context.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
        # ensure proper trader allow_artificial_orders value
        settings.set_allow_artificial_orders(context, context.allow_artificial_orders)
        unknown_portfolio_on_creation = wait_for is not None and any(o.is_open() for o in wait_for)
        input_side = side
        order_quantity, side = await _get_order_quantity_and_side(context, order_amount, order_target_position,
                                                                  order_type_name, input_side, reduce_only,
                                                                  unknown_portfolio_on_creation)

        order_type, order_price, final_side, reduce_only, trailing_method, \
        min_offset_val, max_offset_val, order_limit_offset, limit_offset_val = \
            await _get_order_details(context, order_type_name, side, order_offset, reduce_only, order_limit_offset)

        stop_loss_price = None if stop_loss_offset is None else await script_keywords.get_price_with_offset(
            context, stop_loss_offset
        )
        take_profit_price = None if take_profit_offset is None else await script_keywords.get_price_with_offset(
            context, take_profit_offset
        )
        # round down when not reduce only and up when reduce only to avoid letting small positions open
        truncate = not reduce_only
        return await _create_order(context=context, symbol=symbol, order_quantity=order_quantity,
                                   order_price=order_price, tag=tag, order_type_name=order_type_name,
                                   input_side=input_side, side=side, final_side=final_side,
                                   order_type=order_type, order_min_offset=order_min_offset,
                                   max_offset_val=max_offset_val, reduce_only=reduce_only, group=group,
                                   stop_loss_price=stop_loss_price, stop_loss_tag=stop_loss_tag,
                                   stop_loss_type=stop_loss_type, stop_loss_group=stop_loss_group,
                                   take_profit_price=take_profit_price, take_profit_tag=take_profit_tag,
                                   take_profit_type=take_profit_type, take_profit_group=take_profit_group,
                                   wait_for=wait_for, truncate=truncate, order_amount=order_amount,
                                   order_target_position=order_target_position)


async def _get_order_percents(context, order_amount, order_target_position, input_side, symbol):
    order_pf_percent = None
    if order_amount is not None:
        quantity_type, quantity = script_keywords.parse_quantity(order_amount)
        if quantity_type in (script_keywords.QuantityType.PERCENT, script_keywords.QuantityType.AVAILABLE_PERCENT):
            order_pf_percent = order_amount
        elif quantity_type in (script_keywords.QuantityType.DELTA, script_keywords.QuantityType.DELTA_BASE):
            percent = await script_keywords.get_order_size_portfolio_percent(
                context, quantity, input_side, symbol
            )
            order_pf_percent = f"{float(percent)}{script_keywords.QuantityType.PERCENT.value}"
        else:
            raise trading_errors.InvalidArgumentError(f"Unsupported quantity for trading signals: {order_amount}")
    order_position_percent = None
    if order_target_position is not None:
        quantity_type, quantity = script_keywords.parse_quantity(order_target_position)
        if quantity_type in (script_keywords.QuantityType.PERCENT,
                             script_keywords.QuantityType.AVAILABLE_PERCENT):
            # position out of pf % here
            order_pf_percent = order_target_position
        elif quantity_type is script_keywords.QuantityType.POSITION_PERCENT:
            order_position_percent = order_target_position
        elif quantity_type is script_keywords.QuantityType.DELTA:
            percent = order_target_position * exchange_private_data.open_position_size(context) \
                * trading_constants.ONE_HUNDRED
            order_position_percent = f"{float(percent)}{script_keywords.QuantityType.POSITION_PERCENT.value}"
    return order_pf_percent, order_position_percent


def _paired_order_is_closed(context, group):
    grouped_orders = [] if group is None else group.get_group_open_orders()
    if group is not None and grouped_orders and all(order.is_closed() for order in grouped_orders):
        return True
    for order in context.just_created_orders:
        if order is not None:
            if isinstance(order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)\
               and order.order_group == group and order.is_closed():
                return True
    return False


def _use_total_holding(order_type_name):
    return _is_stop_order(order_type_name)


def _is_stop_order(order_type_name):
    return "stop" in order_type_name


async def _get_order_quantity_and_side(context, order_amount, order_target_position,
                                       order_type_name, side, reduce_only, unknown_portfolio_on_creation):
    if order_amount is not None and order_target_position is not None:
        raise trading_errors.InvalidArgumentError("order_amount and order_target_position can't be "
                                                  "both given as parameter")

    use_total_holding = _use_total_holding(order_type_name)
    is_stop_order = _is_stop_order(order_type_name)
    # size based on amount
    if side is not None and order_amount is not None:
        # side
        if side != trading_enums.TradeOrderSide.BUY.value and side != trading_enums.TradeOrderSide.SELL.value:
            # we should skip that cause of performance
            raise trading_errors.InvalidArgumentError(
                f"Side parameter needs to be {trading_enums.TradeOrderSide.BUY.value} "
                f"or {trading_enums.TradeOrderSide.SELL.value} for your {order_type_name}.")
        return await position_size.get_amount(context, order_amount, side, reduce_only, is_stop_order,
                                              use_total_holding=use_total_holding,
                                              unknown_portfolio_on_creation=unknown_portfolio_on_creation), side

    # size and side based on target position
    if order_target_position is not None:
        return await position_size.get_target_position(context, order_target_position, reduce_only, is_stop_order,
                                                       use_total_holding=use_total_holding,
                                                       unknown_portfolio_on_creation=unknown_portfolio_on_creation)

    raise trading_errors.InvalidArgumentError("Either use side with amount or target_position.")


async def _get_order_details(context, order_type_name, side, order_offset, reduce_only, order_limit_offset):
    # order types
    order_type = None
    final_side = side
    order_price = None
    min_offset_val = None
    max_offset_val = None
    limit_offset_val = None
    trailing_method = None

    # normal order
    if order_type_name == "market":
        order_type = trading_enums.TraderOrderType.SELL_MARKET if side == trading_enums.TradeOrderSide.SELL.value \
            else trading_enums.TraderOrderType.BUY_MARKET
        order_price = await script_keywords.get_price_with_offset(context, "0")
        final_side = None  # needs to be None

    elif order_type_name == "limit":
        order_type = trading_enums.TraderOrderType.SELL_LIMIT if side == trading_enums.TradeOrderSide.SELL.value \
            else trading_enums.TraderOrderType.BUY_LIMIT
        order_price = await script_keywords.get_price_with_offset(context, order_offset)
        final_side = None  # needs to be None
        # todo post only

    # conditional orders
    # should be a real SL on the exchange short and long
    elif order_type_name == "stop_loss":
        order_type = trading_enums.TraderOrderType.STOP_LOSS
        final_side = trading_enums.TradeOrderSide.SELL if side == trading_enums.TradeOrderSide.SELL.value \
            else trading_enums.TradeOrderSide.BUY
        order_price = await script_keywords.get_price_with_offset(context, order_offset)
        reduce_only = True

    # should be conditional order on the exchange
    elif order_type_name == "stop_market":
        order_type = None  # todo
        order_price = await script_keywords.get_price_with_offset(context, order_offset)

    # has a trigger price and a offset where the limit gets placed when triggered -
    # conditional order on exchange possible?
    elif order_type_name == "stop_limit":
        order_type = None  # todo
        order_price = await script_keywords.get_price_with_offset(context, order_offset)
        order_limit_offset = await script_keywords.get_price_with_offset(context, order_offset)
        # todo post only

    # trailling orders
    # should be a real trailing stop loss on the exchange - short and long
    elif order_type_name == "trailing_stop_loss":
        order_price = await script_keywords.get_price_with_offset(context, order_offset)
        order_type = None  # todo
        reduce_only = True
        trailing_method = "continuous"
        # todo make sure order gets replaced by market if price jumped below price before order creation

    # todo should use trailing on exchange if available or replace order on exchange
    elif order_type_name == "trailing_market":
        order_price = await script_keywords.get_price_with_offset(context, order_offset)
        trailing_method = "continuous"
        order_type = trading_enums.TraderOrderType.TRAILING_STOP
        final_side = trading_enums.TradeOrderSide.SELL if side == trading_enums.TradeOrderSide.SELL.value \
            else trading_enums.TradeOrderSide.BUY

    # todo should use trailing on exchange if available or replace order on exchange
    elif order_type_name == "trailing_limit":
        order_type = trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
        final_side = trading_enums.TradeOrderSide.SELL if side == trading_enums.TradeOrderSide.SELL.value \
            else trading_enums.TradeOrderSide.BUY
        trailing_method = "continuous"
        min_offset_val = await script_keywords.get_price_with_offset(context, order_offset)
        # todo If the price changes such that the order becomes more than maxOffset away from the
        #  price, then the order will be moved to minOffset away again.
        max_offset_val = await script_keywords.get_price_with_offset(context, order_offset)
        # todo post only

    return order_type, order_price, final_side, reduce_only, trailing_method, \
           min_offset_val, max_offset_val, order_limit_offset, limit_offset_val


async def _create_order(context, symbol, order_quantity, order_price, tag, order_type_name, input_side, side,
                        final_side,
                        order_type, order_min_offset, max_offset_val, reduce_only, group,
                        stop_loss_price, stop_loss_tag, stop_loss_type, stop_loss_group,
                        take_profit_price, take_profit_tag, take_profit_type, take_profit_group,
                        wait_for, truncate, order_amount, order_target_position):
    # todo handle offsets, reduce_only, post_only,
    orders = []
    error_message = ""
    chained_orders_group = _get_group_or_default(context, group, stop_loss_price, take_profit_price)
    order_pf_percent = order_position_percent = None
    if basic_keywords.is_emitting_trading_signals(context):
        order_pf_percent, order_position_percent = await _get_order_percents(context, order_amount,
                                                                             order_target_position, input_side, symbol)
    try:
        fees_currency_side = None
        if context.exchange_manager.is_future:
            fees_currency_side = context.exchange_manager.exchange.get_pair_contract(symbol).\
                get_fees_currency_side()
        _, _, _, current_price, symbol_market = \
            await trading_personal_data.get_pre_order_data(context.exchange_manager,
                                                           symbol=symbol,
                                                           timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
        group_adapted_quantity = _get_group_adapted_quantity(context, group, order_type, order_quantity)
        for final_order_quantity, final_order_price in \
                trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                    group_adapted_quantity,
                    order_price,
                    symbol_market,
                    truncate=truncate
                ):
            if not truncate:
                # ensure enough money to trade (because of upper rounding)
                available_acc_bal = await script_keywords.available_account_balance(
                    context, side, use_total_holding=_use_total_holding(order_type_name),
                    is_stop_order=_is_stop_order(order_type_name), reduce_only=reduce_only)
                if final_order_quantity > available_acc_bal:
                    final_order_quantity = trading_personal_data.decimal_adapt_quantity(
                        symbol_market, available_acc_bal, truncate=True
                    )
            created_order = trading_personal_data.create_order_instance(
                trader=context.trader,
                order_type=order_type,
                symbol=symbol,
                current_price=current_price,
                quantity=final_order_quantity,
                price=final_order_price,
                side=final_side,
                tag=tag,
                group=group,
                reduce_only=reduce_only,
                fees_currency_side=fees_currency_side
            )
            if order_min_offset is not None:
                await created_order.set_trailing_percent(order_min_offset)
            if wait_for:
                chained_orders = await chaining.chain_order(wait_for, created_order)
            else:
                stop_loss_take_profit_quantity = final_order_quantity
                fees = created_order.get_computed_fee()
                if fees[trading_enums.FeePropertyColumns.CURRENCY.value] == created_order.quantity_currency:
                    stop_loss_take_profit_quantity = final_order_quantity - \
                                                     fees[trading_enums.FeePropertyColumns.COST.value]
                    stop_loss_take_profit_quantity = trading_personal_data.decimal_adapt_quantity(
                        symbol_market, stop_loss_take_profit_quantity, truncate=True
                    )
                params = await _bundle_stop_loss_and_take_profit(
                    context, symbol_market, fees_currency_side, created_order, stop_loss_take_profit_quantity,
                    chained_orders_group,
                    stop_loss_tag, stop_loss_type, stop_loss_price, stop_loss_group,
                    take_profit_tag, take_profit_type, take_profit_price, take_profit_group,
                    order_pf_percent, order_position_percent)
                chained_orders = created_order.chained_orders
                created_order = await context.trader.create_order(created_order, params=params)
            if basic_keywords.is_emitting_trading_signals(context):
                context.get_signal_builder().add_created_order(created_order, context.trader.exchange_manager,
                                                               order_pf_percent, order_position_percent)
            created_chained_orders = [order
                                      for order in chained_orders
                                      if order.is_created()]
            # add chained order if any
            context.just_created_orders += created_chained_orders
            if wait_for:
                # base order to be created are actually the chained orders, return them if created
                orders += created_chained_orders
            else:
                # add create base order
                orders.append(created_order)
                context.just_created_orders.append(created_order)
    except (trading_errors.MissingFunds, trading_errors.MissingMinimalExchangeTradeVolume):
        error_message = "missing minimal funds"
    except asyncio.TimeoutError as e:
        error_message = f"{e} and is necessary to compute the order details"
    except Exception as e:
        error_message = f"failed to create order : {e}."
        context.logger.exception(e, True, f"Failed to create order : {e}.")
    if not orders:
        error_message = f"not enough funds"
    if error_message:
        context.logger.warning(f"No order created when asking for {symbol} {order_type.name} "
                               f"with a volume of {order_quantity} on {context.exchange_manager.exchange_name}: "
                               f"{error_message}.")
    return orders


def _get_group_adapted_quantity(context, group, order_type, order_quantity):
    if isinstance(group, trading_personal_data.BalancedTakeProfitAndStopOrderGroup) and context.just_created_orders:
        all_take_profit = all_stop = True
        is_creating_stop_order = trading_personal_data.is_stop_order(order_type)

        for order in context.just_created_orders:
            if order.order_group == group:
                if trading_personal_data.is_stop_order(order.order_type):
                    all_take_profit = False
                else:
                    all_stop = False
        if (is_creating_stop_order and all_stop) or (not is_creating_stop_order and all_take_profit):
            # we are only creating stop / take profit orders, no need to balance
            return order_quantity
        # we are now adding the order side of the orders, we need to balance
        if group.can_create_order(order_type, order_quantity):
            return order_quantity
        return group.get_max_order_quantity(order_type)
    return order_quantity


def _get_group_or_default(context, group, stop_loss_price, take_profit_price):
    if stop_loss_price is not None or take_profit_price is not None:
        # orders have to be bundled together, group them
        if group is None:
            # use balanced group by default
            return grouping.create_balanced_take_profit_and_stop_group(context)
        else:
            return group
    return group


async def _bundle_stop_loss_and_take_profit(
        context, symbol_market, fees_currency_side, order, quantity, default_group,
        stop_loss_tag, stop_loss_type, stop_loss_price, stop_loss_group,
        take_profit_tag, take_profit_type, take_profit_price, take_profit_group,
        order_pf_percent, order_position_percent) -> dict:
    params = {}
    side = trading_enums.TradeOrderSide.SELL if order.side is trading_enums.TradeOrderSide.BUY \
        else trading_enums.TradeOrderSide.BUY
    order_kwargs = {
        "fees_currency_side": fees_currency_side,
        "reduce_only": True
    }
    if stop_loss_price is not None:
        order_type = stop_loss_type if stop_loss_type else trading_enums.TraderOrderType.STOP_LOSS
        params.update(
            await _bundle_chained_order(context, symbol_market, order, quantity, default_group, side, order_kwargs,
                                        stop_loss_tag, order_type, stop_loss_price, stop_loss_group,
                                        order_pf_percent, order_position_percent)
        )
    if take_profit_price is not None:
        if take_profit_type:
            order_type = take_profit_type
        else:
            order_type = trading_enums.TraderOrderType.BUY_LIMIT if side is trading_enums.TradeOrderSide.BUY \
                else trading_enums.TraderOrderType.SELL_LIMIT
        params.update(
            await _bundle_chained_order(context, symbol_market, order, quantity, default_group, None, order_kwargs,
                                        take_profit_tag, order_type, take_profit_price, take_profit_group,
                                        order_pf_percent, order_position_percent)
        )
    return params


async def _bundle_chained_order(context, symbol_market, order, quantity, default_group, side, order_kwargs,
                                tag, order_type, price, group, order_pf_percent, order_position_percent) -> dict:
    adapted_price = trading_personal_data.decimal_adapt_price(symbol_market, price)
    group = default_group if group is None else group
    chained_order = trading_personal_data.create_order_instance(
        trader=context.trader,
        order_type=order_type,
        symbol=order.symbol,
        current_price=order.created_last_price,
        quantity=quantity,
        price=adapted_price,
        side=side,
        tag=tag,
        group=group,
        **order_kwargs
    )
    params = await context.trader.bundle_chained_order_with_uncreated_order(
        order, chained_order, chained_order.update_with_triggering_order_fees
    )
    if basic_keywords.is_emitting_trading_signals(context):
        context.get_signal_builder().add_created_order(chained_order, context.trader.exchange_manager,
                                                       order_pf_percent, order_position_percent)
    return params
