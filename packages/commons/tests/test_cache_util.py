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
import asyncio
import pytest

import octobot_commons.cache_util as cache_util

pytestmark = pytest.mark.asyncio


class _TestClass:
    def __init__(self):
        self.call_count = 0

    @cache_util.prevented_multiple_calls
    async def decorated_method(self, *args, **kwargs):
        self.call_count += 1
        return self.call_count


async def test_prevented_multiple_calls_without_max_period():
    """Without max_period, function should always be called."""
    obj = _TestClass()
    await obj.decorated_method(max_period=None)
    await obj.decorated_method(max_period=None)
    await obj.decorated_method(max_period=None)
    assert obj.call_count == 3


async def test_prevented_multiple_calls_with_max_period_blocks_duplicate():
    """With max_period, duplicate calls within period should be skipped."""
    obj = _TestClass()
    # First call executes
    result1 = await obj.decorated_method(1, 2, max_period=1.0)
    assert result1 == 1
    assert obj.call_count == 1

    # Second call with same args within period is skipped
    result2 = await obj.decorated_method(1, 2, max_period=1.0)
    assert result2 is None
    assert obj.call_count == 1


async def test_prevented_multiple_calls_with_max_period_allows_after_period():
    """With max_period, call after period should execute."""
    obj = _TestClass()
    result1 = await obj.decorated_method(1, max_period=0.05)
    assert result1 == 1

    await asyncio.sleep(0.06)
    result2 = await obj.decorated_method(1, max_period=0.05)
    assert result2 == 2
    assert obj.call_count == 2


async def test_prevented_multiple_calls_different_args_independent():
    """Different args should have independent cache entries."""
    obj = _TestClass()
    await obj.decorated_method(1, max_period=1.0)
    await obj.decorated_method(2, max_period=1.0)
    await obj.decorated_method(1, max_period=1.0)  # Same as first, skipped
    await obj.decorated_method(2, max_period=1.0)  # Same as second, skipped
    assert obj.call_count == 2


async def test_prevented_multiple_calls_with_kwargs():
    """kwargs should be part of the cache key."""
    obj = _TestClass()
    await obj.decorated_method(1, max_period=1.0, key="a")
    await obj.decorated_method(1, max_period=1.0, key="b")  # Different kwargs
    await obj.decorated_method(1, max_period=1.0, key="a")  # Same as first, skipped
    assert obj.call_count == 2
