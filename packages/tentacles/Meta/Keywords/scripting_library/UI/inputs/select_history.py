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

import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.constants as trading_constants


async def set_candles_history_size(
        ctx,
        def_val=trading_constants.DEFAULT_CANDLE_HISTORY_SIZE,
        name=trading_constants.CONFIG_CANDLES_HISTORY_SIZE_TITLE,
        show_in_summary=False,
        show_in_optimizer=False,
        order=999,
):
    return await basic_keywords.user_input(ctx, name, "int", def_val,
                                           show_in_summary=show_in_summary, show_in_optimizer=show_in_optimizer,
                                           order=order)
