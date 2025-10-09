import datetime


def get_utc_timestamp_from_datetime(dt: datetime.datetime) -> float:
    """
    Convert a datetime to a timestamp in UTC
    WARNING: usable here as we know this DB stores time in UTC only
    """
    return dt.replace(tzinfo=datetime.timezone.utc).timestamp()


def deduplicate(elements, keys: list) -> list:
    # from https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    elements_and_signature = (
        (element, "".join(str(element[key]) for key in keys))
        for element in elements
    )
    return [x for x, s in elements_and_signature if not (s in seen or seen_add(s))]
