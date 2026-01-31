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

import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data


async def total_account_balance(context, side=trading_enums.PositionSide.BOTH.value):
    current_price = \
        await trading_personal_data.get_up_to_date_price(context.exchange_manager,
                                                         symbol=context.symbol,
                                                         timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
    if current_price == trading_constants.ZERO:
        raise trading_errors.InvalidArgumentError("Current asset price is 0")
    on_inverse_contract = False
    if context.exchange_manager.is_future:
        # for BTC/USD
        # on linear, return balance in currency (ex: BTC)
        # on inverse, return balance in market (ex: USD)
        on_inverse_contract = context.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
            context.symbol, trading_enums.PositionSide(side)
        ).symbol_contract.is_inverse_contract()
    value = context.exchange_manager.exchange_personal_data.\
        portfolio_manager.portfolio_value_holder.portfolio_current_value
    base, quote = symbol_util.parse_symbol(context.symbol).base_and_quote()
    reference_market = context.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
    if reference_market == quote:
        return value if on_inverse_contract else value / current_price
    if reference_market == base:
        return value * current_price if on_inverse_contract else value
    raise NotImplementedError(f"Impossible to compute total account balance for a symbol that doesn't contain "
                              f"the reference market. reference market: {reference_market}, symbol: {context.symbol}")


async def available_account_balance(
    context, side=trading_enums.TradeOrderSide.BUY.value, use_total_holding=False,
    is_stop_order=False, reduce_only=True, target_price=None, orders_to_be_ignored=None
):
    portfolio_type = commons_constants.PORTFOLIO_TOTAL if use_total_holding else commons_constants.PORTFOLIO_AVAILABLE
    current_symbol_holding, _, market_quantity, price, _ = \
        await trading_personal_data.get_pre_order_data(context.exchange_manager,
                                                       symbol=context.symbol,
                                                       timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                       portfolio_type=portfolio_type,
                                                       target_price=target_price)
    if context.exchange_manager.is_future:
        max_order_size, _ = trading_personal_data.get_futures_max_order_size(
            context.exchange_manager, context.symbol, trading_enums.TradeOrderSide(side), price, reduce_only,
            current_symbol_holding, market_quantity
        )
        return max_order_size
    already_locked_amount = trading_constants.ZERO
    if use_total_holding and is_stop_order:
        already_locked_amount = _get_locked_amount_in_stop_orders(context, side)
    if orders_to_be_ignored:
        for order_to_be_ignored in orders_to_be_ignored:
            if order_to_be_ignored.side == trading_enums.TradeOrderSide.BUY:
                market_quantity += order_to_be_ignored.origin_quantity
            else:
                current_symbol_holding += order_to_be_ignored.origin_quantity
        total_symbol_holding, _, total_market_quantity, _, _ = \
            await trading_personal_data.get_pre_order_data(context.exchange_manager,
                                                           symbol=context.symbol,
                                                           timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                           portfolio_type=commons_constants.PORTFOLIO_TOTAL,
                                                           target_price=target_price)
        # ensure not using more than total amounts
        current_symbol_holding = min(current_symbol_holding, total_symbol_holding)
        market_quantity = min(market_quantity, total_market_quantity)
    return (market_quantity if side == trading_enums.TradeOrderSide.BUY.value else current_symbol_holding) \
        - already_locked_amount


def _get_locked_amount_in_stop_orders(context, side):
    locked_amount = trading_constants.ZERO
    for order in context.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(context.symbol):
        if isinstance(order, (trading_personal_data.StopLossOrder, trading_personal_data.StopLossLimitOrder)) and \
           order.side.value == side:
            locked_amount += order.origin_quantity
    return locked_amount


async def adapt_amount_to_holdings(
    context, amount, side, use_total_holding, reduce_only,
    is_stop_order, target_price=None, orders_to_be_ignored=None
):
    available_acc_bal = await available_account_balance(
        context, side, use_total_holding=use_total_holding, is_stop_order=is_stop_order,
        reduce_only=reduce_only, target_price=target_price, orders_to_be_ignored=orders_to_be_ignored
    )
    if available_acc_bal > amount:
        return amount
    else:
        return available_acc_bal


def account_holdings(context, currency):
    return context.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.\
        get_currency_portfolio(currency).total


async def get_order_size_portfolio_percent(context, order_amount, input_side, symbol):
    try:
        return await trading_personal_data.get_order_size_portfolio_percent(
            context.exchange_manager,
            order_amount,
            trading_enums.TradeOrderSide(input_side),
            symbol
        )
    except ValueError:
        raise trading_errors.InvalidArgumentError(f"Unknown side: {input_side}")
