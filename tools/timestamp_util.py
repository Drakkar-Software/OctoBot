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
