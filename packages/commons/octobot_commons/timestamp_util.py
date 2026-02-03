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

from datetime import datetime, timezone


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


def convert_timestamp_to_datetime(
    timestamp: float, time_format: str = "%d/%m/%y %H:%M", local_timezone: bool = False
) -> str:
    """
    Convert a timestamp to a human readable string
    :param timestamp: the timestamp to convert
    :param time_format: the time format
    :param local_timezone: if the local timezone should be used
    :return: the created readable string
    """
    return datetime.fromtimestamp(
        timestamp, tz=(LOCAL_TIMEZONE if local_timezone else timezone.utc)
    ).strftime(time_format)


def convert_timestamps_to_datetime(
    timestamps: list[float],
    time_format: str = "%d/%m/%y %H:%M",
    local_timezone: bool = False,
) -> list[str]:
    """
    Convert multiple timestamps to datetime objects
    :param timestamps: the timestamp to convert list
    :param time_format: the time format
    :param local_timezone: if the local timezone should be used
    :return: the created datetime objects
    """
    return [
        convert_timestamp_to_datetime(
            timestamp, time_format=time_format, local_timezone=local_timezone
        )
        for timestamp in timestamps
    ]


def is_valid_timestamp(timestamp: float) -> bool:
    """
    Check if the timestamp is valid
    :param timestamp: the timestamp to check
    :return: the check result
    """
    if timestamp:
        try:
            datetime.fromtimestamp(timestamp)
        except (OSError, ValueError, OverflowError, TypeError):
            return False
    return True


def get_now_time(
    time_format: str = "%Y-%m-%d %H:%M:%S", local_timezone: bool = True
) -> str:
    """
    Get the current time
    :param time_format: the time format
    :return: the current timestamp
    """
    return datetime.now(
        tz=(LOCAL_TIMEZONE if local_timezone else timezone.utc)
    ).strftime(time_format)


def datetime_to_timestamp(
    date_time_str: str, date_time_format: str, local_timezone: bool = True
) -> float:
    """
    Convert a datetime to timestamp
    :param date_time_str: the datetime string
    :param date_time_format: the datetime format
    :return: the timestamp
    """
    return create_datetime_from_string(
        date_time_str, date_time_format, local_timezone=local_timezone
    ).timestamp()


def create_datetime_from_string(
    date_time_str: str, date_time_format: str, local_timezone: bool = True
) -> datetime:
    """
    Convert a string to datetime
    :param date_time_str: the datetime string
    :param date_time_format: the datetime format
    :return: the converted datetime
    """
    # force local timezone or parsing might fail
    return datetime.strptime(date_time_str, date_time_format).replace(
        tzinfo=LOCAL_TIMEZONE if local_timezone else timezone.utc
    )
