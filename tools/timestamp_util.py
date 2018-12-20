#  Drakkar-Software OctoBot
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
from datetime import datetime

_EPOCH = time.time()
TIMEZONE_DELTA = datetime.fromtimestamp(_EPOCH) - datetime.utcfromtimestamp(_EPOCH)


def convert_timestamp_to_datetime(timestamp, time_format='%d/%m/%y %H:%M', force_timezone=False):
    if force_timezone:
        timestamp += TIMEZONE_DELTA.seconds
    return datetime.fromtimestamp(timestamp).strftime(time_format)


def convert_timestamps_to_datetime(timestamps, time_format='%d/%m/%y %H:%M', force_timezone=False):
    return [convert_timestamp_to_datetime(timestamp, time_format=time_format, force_timezone=force_timezone)
            for timestamp in timestamps]


def is_valid_timestamp(timestamp):
    if timestamp:
        try:
            datetime.fromtimestamp(timestamp)
        except OSError:
            return False
        except ValueError:
            return False
        except OverflowError:
            return False
    return True


def get_now_time(time_format='%Y-%m-%d %H:%M:%S'):
    return datetime.fromtimestamp(time.time()).strftime(time_format)
