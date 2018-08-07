import time
from datetime import datetime

_EPOCH = time.time()
TIMEZONE_DELTA = datetime.fromtimestamp(_EPOCH) - datetime.utcfromtimestamp(_EPOCH)


def convert_timestamp_to_datetime(timestamp, format='%d/%m/%y %H:%M', force_timezone=False):
    if force_timezone:
        timestamp += TIMEZONE_DELTA.seconds
    return datetime.fromtimestamp(timestamp).strftime(format)


def convert_timestamps_to_datetime(timestamps, format='%d/%m/%y %H:%M', force_timezone=False):
    return [convert_timestamp_to_datetime(timestamp, format=format, force_timezone=force_timezone)
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
