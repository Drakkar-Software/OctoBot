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

import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.matrix as matrix


async def user_select_time_frame(
        ctx,
        def_val="1h",
        name="Timeframe",
        show_in_summary=True,
        show_in_optimizer=True,
        order=None
):
    available_timeframes = time_frame_manager.sort_time_frames(ctx.exchange_manager.client_time_frames)
    selected_timeframe = await basic_keywords.user_input(ctx, name, "options", def_val, options=available_timeframes,
                                                         show_in_summary=show_in_summary,
                                                         show_in_optimizer=show_in_optimizer, order=order)
    return selected_timeframe


async def user_multi_select_time_frame(
        ctx,
        def_val="1h",
        name="Timeframe",
        show_in_summary=True,
        show_in_optimizer=True,
        order=None
):
    available_timeframes = time_frame_manager.sort_time_frames(ctx.exchange_manager.client_time_frames)
    selected_timeframe = await basic_keywords.user_input(ctx, name, "multiple-options", def_val,
                                                         options=available_timeframes, show_in_summary=show_in_summary,
                                                         show_in_optimizer=show_in_optimizer, order=order)
    return selected_timeframe


async def set_trigger_time_frames(
        ctx,
        def_val=None,
        show_in_summary=True,
        show_in_optimizer=False,
        order=None
):
    available_timeframes = [
        tf.value
        for tf in time_frame_manager.sort_time_frames(
            ctx.exchange_manager.exchange_config.get_relevant_time_frames()
        )
    ]
    def_val = def_val or available_timeframes[0]
    name = commons_constants.CONFIG_TRIGGER_TIMEFRAMES.replace("_", " ")
    trigger_timeframes = await basic_keywords.user_input(ctx, name, "multiple-options", def_val,
                                                         options=available_timeframes, show_in_summary=show_in_summary,
                                                         show_in_optimizer=show_in_optimizer, flush_if_necessary=True,
                                                         order=order)
    if ctx.time_frame not in trigger_timeframes:
        if isinstance(ctx.tentacle, evaluators.AbstractEvaluator):
            # For evaluators, make sure that undesired time frames are not in matrix anymore.
            # Otherwise a strategy might wait for their value before pushing its evaluation to trading modes
            matrix.delete_tentacle_node(
                matrix_id=ctx.tentacle.matrix_id,
                tentacle_path=matrix.get_matrix_default_value_path(
                    exchange_name=ctx.exchange_manager.exchange_name,
                    tentacle_type=ctx.tentacle.evaluator_type.value,
                    tentacle_name=ctx.tentacle.get_name(),
                    cryptocurrency=ctx.cryptocurrency,
                    symbol=ctx.symbol,
                    time_frame=ctx.time_frame if ctx.time_frame else None
                )
            )
        raise commons_errors.ExecutionAborted(f"Execution aborted: disallowed time frame: {ctx.time_frame}")
    return trigger_timeframes
