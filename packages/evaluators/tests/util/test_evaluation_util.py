#  Drakkar-Software OctoBot-Evaluators
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
import pytest

from octobot_commons.enums import PriceIndexes, TimeFrames
from octobot_evaluators.util.evaluation_util import get_eval_time, get_shortest_time_frame


def test_get_eval_time():
    candle = []
    candle.insert(PriceIndexes.IND_PRICE_TIME.value, 123456)
    partial_candle = []
    partial_candle.insert(PriceIndexes.IND_PRICE_TIME.value, 1234567)
    kline = []
    kline.insert(PriceIndexes.IND_PRICE_TIME.value, 12345678)
    assert get_eval_time(full_candle=candle, time_frame=TimeFrames.ONE_HOUR) == 123456 + 60 * 60
    assert get_eval_time(partial_candle=partial_candle) == 1234567
    assert get_eval_time(kline=kline) == 12345678


def test_get_shortest_time_frame():
    pref_time_frames = [TimeFrames.ONE_HOUR, TimeFrames.ONE_DAY, TimeFrames.ONE_MONTH]
    assert get_shortest_time_frame(TimeFrames.ONE_HOUR, pref_time_frames, []) == TimeFrames.ONE_HOUR
    assert get_shortest_time_frame(TimeFrames.ONE_MINUTE, pref_time_frames, [TimeFrames.ONE_WEEK]) == TimeFrames.ONE_HOUR
    assert get_shortest_time_frame(TimeFrames.ONE_MINUTE, [], [TimeFrames.ONE_MONTH]) == TimeFrames.ONE_MONTH
    assert get_shortest_time_frame(TimeFrames.ONE_MINUTE, [], [TimeFrames.ONE_MONTH, TimeFrames.ONE_DAY]) == TimeFrames.ONE_DAY
    assert get_shortest_time_frame(TimeFrames.ONE_MINUTE, [], [TimeFrames.ONE_HOUR, TimeFrames.ONE_MONTH]) == TimeFrames.ONE_HOUR
