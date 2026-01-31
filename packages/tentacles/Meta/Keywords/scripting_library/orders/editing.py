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
import decimal

import octobot_trading.constants as trading_constants
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords


async def edit_order(ctx, order,
                     edited_quantity: decimal.Decimal = None,
                     edited_price: decimal.Decimal = None,
                     edited_stop_price: decimal.Decimal = None,
                     edited_current_price: decimal.Decimal = None,
                     params: dict = None) -> bool:
    if not ctx.enable_trading:
        return False
    changed = await ctx.trader.edit_order(
        order,
        edited_quantity=edited_quantity,
        edited_price=edited_price,
        edited_stop_price=edited_stop_price,
        edited_current_price=edited_current_price,
        params=params,
    )
    if basic_keywords.is_emitting_trading_signals(ctx):
        ctx.get_signal_builder().add_edited_order(
            order,
            ctx.trader.exchange_manager,
            updated_quantity=trading_constants.ZERO if edited_quantity is None else edited_quantity,
            updated_limit_price=trading_constants.ZERO if edited_price is None else edited_price,
            updated_stop_price=trading_constants.ZERO if edited_stop_price is None else edited_stop_price,
            updated_current_price=trading_constants.ZERO if edited_current_price is None else edited_current_price
        )
    return changed
