import datetime


def convert_timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)


def convert_timestamps_to_datetime(timestamps):
    return [convert_timestamp_to_datetime(timestamp) for timestamp in timestamps]


def is_valid_timestamp(timestamp):
    if timestamp:
        try:
            datetime.datetime.fromtimestamp(timestamp)
        except OSError:
            return False
        except ValueError:
            return False
        except OverflowError:
            return False
    return True
