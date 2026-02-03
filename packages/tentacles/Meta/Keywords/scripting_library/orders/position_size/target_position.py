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

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.modes.script_keywords as script_keywords
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_private_data as exchange_private_data


# todo handle negative open position for shorts
async def get_target_position(
        context=None,
        target=None,
        reduce_only=True,
        is_stop_order=False,
        use_total_holding=False,
        unknown_portfolio_on_creation=False,
        target_price=None
):
    target_position_type, target_position_value = script_keywords.parse_quantity(target)

    if target_position_type is script_keywords.QuantityType.POSITION_PERCENT:
        open_position_size_val = exchange_private_data.open_position_size(context)
        target_size = open_position_size_val * target_position_value / 100
        order_size = target_size - open_position_size_val

    elif target_position_type is script_keywords.QuantityType.PERCENT:
        total_acc_bal = await script_keywords.total_account_balance(context)
        target_size = total_acc_bal * target_position_value / 100
        order_size = target_size - exchange_private_data.open_position_size(context)

    # in target position, we always provide the position size we want to end up with
    elif target_position_type in (script_keywords.QuantityType.DELTA, script_keywords.QuantityType.DELTA_BASE) \
            or target_position_type is script_keywords.QuantityType.FLAT:
        order_size = target_position_value - exchange_private_data.open_position_size(context)
        if target == order_size:
            # no order to create
            return trading_constants.ZERO, trading_enums.TradeOrderSide.BUY.value

    elif target_position_type is script_keywords.QuantityType.AVAILABLE_PERCENT:
        available_account_balance_val = await script_keywords.available_account_balance(context,
                                                                                        reduce_only=reduce_only)
        order_size = available_account_balance_val * target_position_value / 100

    else:
        raise trading_errors.InvalidArgumentError("make sure to use a supported syntax for position")

    side = get_target_position_side(order_size)
    if side == trading_enums.TradeOrderSide.SELL.value:
        order_size = order_size * -1
    if not unknown_portfolio_on_creation:
        order_size = await script_keywords.adapt_amount_to_holdings(context, order_size, side,
                                                                    use_total_holding, reduce_only, is_stop_order,
                                                                    target_price=target_price)
    return order_size, side


def get_target_position_side(order_size):
    if order_size < 0:
        return trading_enums.TradeOrderSide.SELL.value
    elif order_size > 0:
        return trading_enums.TradeOrderSide.BUY.value
    # order_size == 0
    raise RuntimeError("Computed position size is 0")
