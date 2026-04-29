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
import numpy

import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import octobot_trading.modes.script_keywords as script_keywords
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants


async def disable_candles_plot(ctx, time_frame=None):
    time_frame = time_frame or ctx.time_frame
    if not ctx.symbol_writer.are_data_initialized_by_key.get(time_frame):
        await script_keywords.disable_candles_plot(None, ctx.exchange_manager)


async def plot(ctx, title, x=None,
               y=None, z=None, open=None, high=None, low=None, close=None, volume=None,
               text=None, kind="scattergl", mode="lines", line_shape="linear",
               condition=None, x_function=exchange_public_data.Time,
               x_multiplier=1000, time_frame=None,
               chart=commons_enums.PlotCharts.SUB_CHART.value,
               cache_value=None, own_yaxis=False, color=None, size=None, shape=None,
               shift_to_open_candle_time=True):
    time_frame = time_frame or ctx.time_frame
    if condition is not None and cache_value is None:
        if isinstance(ctx.symbol_writer.get_serializable_value(condition), bool):
            if condition:
                x = numpy.array(((await x_function(ctx, ctx.symbol, time_frame))[-1],))
                y = numpy.array((y[-1],))
            else:
                x = []
                y = []
        else:
            candidate_y = []
            candidate_x = []
            x_data = (await x_function(ctx, ctx.symbol, time_frame))[-len(condition):]
            y_data = y[-len(condition):]
            for index, value in enumerate(condition):
                if value:
                    candidate_y.append(y_data[index])
                    candidate_x.append(x_data[index])
            x = numpy.array(candidate_x)
            y = numpy.array(candidate_y)
    count_query = {
        "time_frame": ctx.time_frame,
    }
    cache_full_path = None
    if cache_value is not None:
        cache_full_path = ctx.get_cache_path(ctx.tentacle)
        count_query["title"] = title
        count_query["value"] = cache_full_path

    x_shift = -commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(ctx.time_frame)] * \
        commons_constants.MINUTE_TO_SECONDS if shift_to_open_candle_time else 0
    if not await ctx.symbol_writer.contains_row(
            commons_enums.DBTables.CACHE_SOURCE.value if cache_value is not None else title,
            count_query
    ):
        if cache_value is not None:
            table = commons_enums.DBTables.CACHE_SOURCE.value
            # save x_shift to be applied when displaying and not to change actual cached values
            cache_data = {
                "title": title,
                "text": text,
                "time_frame": ctx.time_frame,
                "value": cache_full_path,
                "cache_value": cache_value,
                "kind": kind,
                "mode": mode,
                "line_shape": line_shape,
                "chart": chart,
                "own_yaxis": own_yaxis,
                "condition": condition,
                "color": color,
                "size": size,
                "shape": shape,
                "x_shift": x_shift,
            }
            update_query = await ctx.symbol_writer.search()
            update_query = ((update_query.kind == kind)
                            & (update_query.mode == mode)
                            & (update_query.time_frame == ctx.time_frame)
                            & (update_query.title == title))
            await ctx.symbol_writer.upsert(table, cache_data, update_query)
        else:
            adapted_x = None
            if x is not None:
                try:
                    min_available_data = len(x)
                except TypeError:
                    min_available_data = None
                if y is not None:
                    min_available_data = len(y)
                    if isinstance(y, list) and not isinstance(x, list):
                        x = [x] * len(y)
                if z is not None:
                    min_available_data = len(z) if min_available_data is None else min(min_available_data, len(z))
                    if isinstance(z, list) and not isinstance(z, list):
                        x = [x] * len(z)
                adapted_x = x[-min_available_data:] if min_available_data != len(x) else x
            if adapted_x is None:
                raise RuntimeError("No confirmed adapted_x")
            adapted_x = [(a_x + x_shift) * x_multiplier for a_x in adapted_x] if isinstance(adapted_x, list) \
                else adapted_x * x_multiplier
            await ctx.symbol_writer.log_many(
                title,
                [
                    {
                        "x": value,
                        "y": _get_value_from_array(y, index),
                        "z": _get_value_from_array(z, index),
                        "open": _get_value_from_array(open, index),
                        "high": _get_value_from_array(high, index),
                        "low": _get_value_from_array(low, index),
                        "close": _get_value_from_array(close, index),
                        "volume": _get_value_from_array(volume, index),
                        "time_frame": ctx.time_frame,
                        "kind": kind,
                        "mode": mode,
                        "line_shape": line_shape,
                        "chart": chart,
                        "own_yaxis": own_yaxis,
                        "color": color,
                        "text": text,
                        "size": size,
                        "shape": shape,
                    }
                    for index, value in enumerate(adapted_x)
                ],
                cache=False
            )
    elif cache_value is None and x is not None:
        if isinstance(y, list) and not isinstance(x, list):
            x = [x] * len(y)
        elif isinstance(z, list) and not isinstance(x, list):
            x = [x] * len(z)
        if len(x) and \
                not await ctx.symbol_writer.contains_row(title,
                                                   {"x": _get_value_from_array(x, -1) * x_multiplier}):
            x_value = (_get_value_from_array(x, -1) + x_shift) * x_multiplier
            await ctx.symbol_writer.upsert(
                title,
                {
                    "time_frame": ctx.time_frame,
                    "x": x_value,
                    "y": _get_value_from_array(y, -1),
                    "z": _get_value_from_array(z, -1),
                    "open": _get_value_from_array(open, -1),
                    "high": _get_value_from_array(high, -1),
                    "low": _get_value_from_array(low, -1),
                    "close": _get_value_from_array(close, -1),
                    "volume": _get_value_from_array(volume, -1),
                    "kind": kind,
                    "mode": mode,
                    "line_shape": line_shape,
                    "chart": chart,
                    "own_yaxis": own_yaxis,
                    "color": color,
                    "text": text,
                    "size": size,
                    "shape": shape,
                },
                None,
                cache_query={"x": x_value}
            )


async def plot_shape(ctx, title, value, y_value,
                     chart=commons_enums.PlotCharts.SUB_CHART.value,
                     kind="scattergl", mode="markers", line_shape="linear", x_multiplier=1000):
    if not await ctx.symbol_writer.contains_row(title, {
        "x": ctx.x,
        "time_frame": ctx.time_frame
    }):
        await ctx.symbol_writer.log(
            title,
            {
                "time_frame": ctx.time_frame,
                "x": (await exchange_public_data.current_candle_time(ctx)) * x_multiplier,
                "y": y_value,
                "value": ctx.symbol_writer.get_serializable_value(value),
                "kind": kind,
                "mode": mode,
                "line_shape": line_shape,
                "chart": chart,
            }
        )


def _get_value_from_array(array, index, multiplier=1):
    if array is None:
        return None
    return array[index] * multiplier
