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
import time
import mock
from datetime import timezone, timedelta

from octobot_commons.timestamp_util import is_valid_timestamp, get_now_time, datetime_to_timestamp, \
    convert_timestamp_to_datetime


def test_is_valid_timestamp():
    assert not is_valid_timestamp(get_now_time())
    assert is_valid_timestamp(time.time())


def test_datetime_to_timestamp():
    date_str = convert_timestamp_to_datetime(1737331200, time_format="%d/%m/%y %H:%M", local_timezone=True)
    assert datetime_to_timestamp(date_str, "%d/%m/%y %H:%M") == 1737331200


def test_convert_timestamp_to_datetime_default():
    # 1 Jan 2020 00:00 UTC
    ts = 1577836800
    assert convert_timestamp_to_datetime(ts) == "01/01/20 00:00"


def test_convert_timestamp_to_datetime_custom_format():
    ts = 1577836800
    assert convert_timestamp_to_datetime(ts, time_format="%Y-%m-%d") == "2020-01-01"


def test_convert_timestamp_to_datetime_local_timezone(monkeypatch):
    # Patch LOCAL_TIMEZONE to UTC+2 for test
    dummy_tz = timezone(timedelta(hours=2))
    with mock.patch("octobot_commons.timestamp_util.LOCAL_TIMEZONE", dummy_tz):
        ts = 1577836800  # 1 Jan 2020 00:00 UTC
        # Should be 02:00 in UTC+2
        assert convert_timestamp_to_datetime(ts, local_timezone=True) == "01/01/20 02:00"


def test_convert_timestamp_to_datetime_epoch():
    assert convert_timestamp_to_datetime(0) == "01/01/70 00:00"


def test_convert_timestamp_to_datetime_far_future():
    ts = 32503680000  # year 3000
    assert convert_timestamp_to_datetime(ts, time_format="%Y") == "3000"


def test_convert_timestamp_to_datetime_negative():
    # Negative timestamp: before epoch
    ts = -1
    result = convert_timestamp_to_datetime(ts)
    # Should not raise, but result is system-dependent
    assert isinstance(result, str)
