import datetime


def get_utc_timestamp_from_datetime(dt: datetime.datetime) -> float:
    """
    Convert a datetime to a timestamp in UTC
    WARNING: usable here as we know this DB stores time in UTC only
    """
    return dt.replace(tzinfo=datetime.timezone.utc).timestamp()


def deduplicate(elements, key) -> list:
    # from https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in elements if not (x[key] in seen or seen_add(x[key]))]
