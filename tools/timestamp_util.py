import time
from datetime import datetime

_EPOCH = time.time()
TIMEZONE_DELTA = datetime.fromtimestamp(_EPOCH) - datetime.utcfromtimestamp(_EPOCH)


def convert_timestamp_to_datetime(timestamp, format='%d/%m/%y %H:%M'):
    return datetime.fromtimestamp(timestamp_to_local(timestamp)).strftime(format)


def timestamp_to_local(timestamp):
    return timestamp + TIMEZONE_DELTA.seconds


def timestamps_to_local(timestamps):
    return [timestamp_to_local(timestamp)
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
