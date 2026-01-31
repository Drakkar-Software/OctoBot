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
import octobot_backtesting.api as backtesting_api
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data


def backtesting_start_time(ctx):
    return backtesting_api.get_backtesting_starting_time(ctx.exchange_manager.exchange.backtesting)


def backtesting_first_full_candle_time(ctx):
    return _align_time_to_time_frame(backtesting_start_time(ctx), ctx.time_frame, False)


async def backtesting_is_first_full_candle(ctx):
    current_t = await exchange_public_data.current_candle_time(ctx)
    first_c = _align_time_to_time_frame(backtesting_start_time(ctx), ctx.time_frame, False)
    return current_t == first_c


def backtesting_end_time(ctx):
    return backtesting_api.get_backtesting_ending_time(ctx.exchange_manager.exchange.backtesting)


def backtesting_last_full_candle_time(ctx):
    return _align_time_to_time_frame(backtesting_end_time(ctx), ctx.time_frame, True)


def _align_time_to_time_frame(reference_time, time_frame, align_backwards):
    time_frame_sec = commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)] \
        * commons_constants.MINUTE_TO_SECONDS
    time_delta = reference_time % time_frame_sec
    if align_backwards:
        # the last full candle time is the backtesting end time moved back to the start of the candle
        potential_candle_time = reference_time - time_frame_sec
    else:
        # the first full candle time the backtesting start time moved forward to the start of the 1st candle
        potential_candle_time = reference_time - time_frame_sec
        time_delta = time_frame_sec - time_delta if time_delta > 0 else 0
    # align back to the UTC time
    return potential_candle_time - time_delta if align_backwards else potential_candle_time + time_delta

