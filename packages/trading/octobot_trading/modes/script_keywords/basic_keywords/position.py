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

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors


def get_position(context, symbol=None, side=trading_enums.PositionSide.BOTH.value):
    return context.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
        symbol or context.symbol,
        _get_position_side(context, side)
    )


async def average_open_pos_entry(context, side=trading_enums.PositionSide.LONG.value):
    if context.exchange_manager.is_future:
        return get_position(context, context.symbol, side).entry_price
    elif context.exchange_manager.is_margin:
        return trading_constants.ZERO
    else:
        return trading_constants.ZERO


def _get_position_side(ctx, side):
    if is_in_one_way_position_mode(ctx):
        return trading_enums.PositionSide.BOTH

    # hedge mode
    if side == trading_enums.PositionSide.LONG.value:
        return trading_enums.PositionSide.LONG
    elif side == trading_enums.PositionSide.SHORT.value:
        return trading_enums.PositionSide.SHORT
    elif side == trading_enums.PositionSide.BOTH.value:
        raise trading_errors.InvalidArgumentError(
            "average_open_pos_entry: both sides are not implemented yet for hedged mode"
        )
    else:
        raise trading_errors.InvalidArgumentError(
            'average_open_pos_entry: side needs to be "long", "short" or "both"'
        )


def is_in_one_way_position_mode(ctx):
    return ctx.exchange_manager.exchange.get_pair_future_contract(ctx.symbol).is_one_way_position_mode()
