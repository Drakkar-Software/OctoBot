#  Drakkar-Software OctoBot-Commons
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
from octobot_commons.enums import TimeFrames
from octobot_commons.tests.test_config import load_test_config
from octobot_commons.time_frame_manager import get_config_time_frame, parse_time_frames, find_min_time_frame, \
    get_previous_time_frame, get_display_time_frame, sort_time_frames


def test_get_config_time_frame():
    assert get_config_time_frame(load_test_config()) == [TimeFrames("1h"), TimeFrames("4h"), TimeFrames("1d")]


def test_parse_time_frames():
    assert parse_time_frames(["3d", "5d", "1m", "6h"]) == [TimeFrames("3d"), TimeFrames("1m"), TimeFrames("6h")]


def test_sort_time_frames():
    assert sort_time_frames([TimeFrames("3d"), TimeFrames("1m"), TimeFrames("6h")]) == \
           [TimeFrames("1m"), TimeFrames("6h"), TimeFrames("3d")]
    assert sort_time_frames([TimeFrames("1M"), TimeFrames("3d"), TimeFrames("12h"), TimeFrames("1h"),
                             TimeFrames("1m"), TimeFrames("6h")]) == \
           [TimeFrames("1m"), TimeFrames("1h"), TimeFrames("6h"), TimeFrames("12h"), TimeFrames("3d"), TimeFrames("1M")]


def test_find_min_time_frame():
    assert find_min_time_frame([TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY, TimeFrames.ONE_MONTH,
                                TimeFrames.FIFTEEN_MINUTES]) == TimeFrames.FIFTEEN_MINUTES
    assert find_min_time_frame([TimeFrames.ONE_MONTH, TimeFrames.ONE_WEEK]) == TimeFrames.ONE_WEEK
    assert find_min_time_frame([TimeFrames.ONE_MINUTE]) == TimeFrames.ONE_MINUTE


def test_get_previous_time_frame():
    assert get_previous_time_frame(get_config_time_frame(load_test_config()),
                                   TimeFrames.ONE_DAY, TimeFrames.ONE_DAY) == TimeFrames.FOUR_HOURS
    assert get_previous_time_frame(get_config_time_frame(load_test_config()),
                                   TimeFrames.ONE_MINUTE, TimeFrames.ONE_MINUTE) == TimeFrames.ONE_MINUTE
    assert get_previous_time_frame(get_config_time_frame(load_test_config()),
                                   TimeFrames.ONE_HOUR, TimeFrames.ONE_HOUR) == TimeFrames.ONE_HOUR
    assert get_previous_time_frame(get_config_time_frame(load_test_config()),
                                   TimeFrames.ONE_MONTH, TimeFrames.ONE_MONTH) == TimeFrames.ONE_DAY


def test_get_display_time_frame():
    assert get_display_time_frame(load_test_config(), TimeFrames.ONE_MONTH) == TimeFrames.ONE_DAY
    assert get_display_time_frame(load_test_config(), TimeFrames.FOUR_HOURS) == TimeFrames.FOUR_HOURS
