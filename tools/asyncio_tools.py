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

import asyncio

from config import DEFAULT_FUTURE_TIMEOUT
from tools.logging.logging_util import get_logger


def run_coroutine_in_asyncio_loop(coroutine, async_loop):
    future = asyncio.run_coroutine_threadsafe(coroutine, async_loop)
    try:
        return future.result(DEFAULT_FUTURE_TIMEOUT)
    except asyncio.TimeoutError as e:
        get_logger("run_coroutine_in_asyncio_loop")\
            .error(f'{coroutine} coroutine coroutine too long, cancelling the task.')
        future.cancel()
        raise e


async def get_gather_wrapper(tasks):
    await asyncio.gather(*tasks)
