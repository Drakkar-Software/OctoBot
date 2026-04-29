#  Drakkar-Software OctoBot
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
import time


def prevented_multiple_calls(f):
    """
    Decorator to prevent multiple identical calls to a method within a given period.
    """
    _calls_cache: dict[int, float] = {}

    async def _prevented_multiple_calls_wrapper(self, *args, max_period: float = 0, **kwargs):
        if max_period:
            # include self in the hash to avoid mixing calls from different instances
            args_key = hash(f"{id(self)} {hash(args)} {hash(str(kwargs))}")
            if args_key in _calls_cache:
                if time.time() - _calls_cache[args_key] < max_period:
                    # period not reached: skip call
                    return
            # register call
            _calls_cache[args_key] = time.time()
        return await f(self, *args, **kwargs)
    return _prevented_multiple_calls_wrapper
