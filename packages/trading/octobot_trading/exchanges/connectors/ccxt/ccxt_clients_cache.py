#  Drakkar-Software OctoBot-Trading
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
import cachetools
import json
import typing
import contextlib

import octobot_commons.constants as commons_constants


# To avoid side effects related to a cache refresh at a fix time of the day every day,
# cache should not be refreshed at the same time every day.
# Use 30h and 18min as a period. It could be anything else as long as it doesn't make it so
# that cache ends up refreshed approximately at the same time of the day
_CACHE_TIME = commons_constants.HOURS_TO_SECONDS * 30 + commons_constants.MINUTE_TO_SECONDS * 18
_MARKETS_BY_EXCHANGE = cachetools.TTLCache(maxsize=50, ttl=_CACHE_TIME)
# Time difference between system clock and exchange server clock, fetched when needed when loading market statuses
_TIME_DIFFERENCE_BY_EXCHANGE: dict[str, float] = {}

# use short cache time for authenticated markets to avoid caching them for too long
_AUTH_CACHE_TIME = 15 * commons_constants.MINUTE_TO_SECONDS
_AUTH_MARKETS_BY_EXCHANGE = cachetools.TTLCache(maxsize=50, ttl=_AUTH_CACHE_TIME)

_UNAUTHENTICATED_SUFFIX = "unauthenticated"

def get_client_key(client, authenticated_cache: bool) -> str:
    suffix = client.apiKey if authenticated_cache else _UNAUTHENTICATED_SUFFIX
    return f"{client.__class__.__name__}:{json.dumps(client.urls.get('api'))}:{suffix}"


def get_exchange_parsed_markets(client_key: str):
    return _get_cached_markets(client_key)[client_key]


def set_exchange_parsed_markets(client_key: str, markets):
    _get_cached_markets(client_key)[client_key] = markets


def _get_cached_markets(client_key: str) -> cachetools.TTLCache:
    if _is_authenticated_cache(client_key):
        return _AUTH_MARKETS_BY_EXCHANGE
    return _MARKETS_BY_EXCHANGE


def get_exchange_time_difference(client_key: str) -> typing.Optional[float]:
    return _TIME_DIFFERENCE_BY_EXCHANGE.get(client_key, None)

def set_exchange_time_difference(client_key: str, time_difference: float):
    _TIME_DIFFERENCE_BY_EXCHANGE[client_key] = time_difference


def _is_authenticated_cache(client_key: str) -> bool:
    return not client_key.endswith(_UNAUTHENTICATED_SUFFIX)


@contextlib.contextmanager
def isolated_empty_cache():
    # temporarily use an isolated empty cache
    global _MARKETS_BY_EXCHANGE, _AUTH_MARKETS_BY_EXCHANGE  # pylint: disable=global-statement
    previous_markets_by_exchange = _MARKETS_BY_EXCHANGE
    previous_auth_markets_by_exchange = _AUTH_MARKETS_BY_EXCHANGE
    _MARKETS_BY_EXCHANGE = cachetools.TTLCache(maxsize=50, ttl=_CACHE_TIME)
    _AUTH_MARKETS_BY_EXCHANGE = cachetools.TTLCache(maxsize=50, ttl=_AUTH_CACHE_TIME)
    try:
        yield
    finally:
        _MARKETS_BY_EXCHANGE = previous_markets_by_exchange
        _AUTH_MARKETS_BY_EXCHANGE = previous_auth_markets_by_exchange
