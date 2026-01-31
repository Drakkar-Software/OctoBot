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
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data


async def user_select_candle(
        ctx,
        name="Select Candle Source",
        def_val="close",
        time_frame=None,
        symbol=None,
        limit=-1,
        enable_volume=True,
        return_source_name=False,
        max_history=False,
        show_in_summary=True,
        show_in_optimizer=True,
        order=None,
):
    available_data_src = ["open", "high", "low", "close", "hl2", "hlc3", "ohlc4",
                          "Heikin Ashi open", "Heikin Ashi high", "Heikin Ashi low", "Heikin Ashi close"]
    if enable_volume:
        available_data_src.append("volume")

    data_source = await basic_keywords.user_input(ctx, name, "options", def_val, options=available_data_src,
                                                  show_in_summary=show_in_summary, show_in_optimizer=show_in_optimizer,
                                                  order=order)
    candle_source = await exchange_public_data.get_candles_from_name(
        ctx, source_name=data_source, time_frame=time_frame, symbol=symbol, limit=limit, max_history=max_history
    )
    if return_source_name:
        return candle_source, data_source
    else:
        return candle_source
