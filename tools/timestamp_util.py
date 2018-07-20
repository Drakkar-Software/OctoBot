from datetime import datetime
import time
import pytz
import tzlocal


_EPOCH = time.time()
LOCAL_TIMEZONE = tzlocal.get_localzone()
TIMEZONE_DELTA = datetime.fromtimestamp(_EPOCH) - datetime.utcfromtimestamp(_EPOCH)


def convert_timestamp_to_datetime(timestamp, from_timezone=pytz.utc, to_timezone=LOCAL_TIMEZONE, force_timezone=False):
    converted_time = datetime.fromtimestamp(timestamp, tz=from_timezone).astimezone(to_timezone)
    if force_timezone:
        return converted_time + TIMEZONE_DELTA
    return converted_time


def convert_timestamps_to_datetime(timestamps, from_timezone=pytz.utc,
                                   to_timezone=LOCAL_TIMEZONE, force_timezone=False):
    return [convert_timestamp_to_datetime(timestamp, from_timezone, to_timezone, force_timezone)
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
