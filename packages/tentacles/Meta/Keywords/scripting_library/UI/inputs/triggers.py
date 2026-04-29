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


TRIGGER_ONLY_ON_THE_FIRST_CANDLE_KEY = "trigger_only_on_the_first_candle"


async def trigger_only_on_the_first_candle(ctx,
                                           default_value,
                                           show_in_summary=False,
                                           show_in_optimizer=False,
                                           order=700):
    return await basic_keywords.user_input(ctx, TRIGGER_ONLY_ON_THE_FIRST_CANDLE_KEY, "boolean", default_value,
                                           show_in_summary=show_in_summary,
                                           show_in_optimizer=show_in_optimizer,
                                           order=order)
