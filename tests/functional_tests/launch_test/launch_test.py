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

from asyncio import CancelledError
import pytest

from config import *
from octobot import OctoBot
from tests.test_utils.config import load_test_config


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_run_bot(event_loop):
    # launch a bot
    config = load_test_config()
    config[CONFIG_CRYPTO_CURRENCIES] = {
        "Bitcoin":
            {
                "pairs": ["BTC/USDT"]
            }
    }
    bot = OctoBot(config)
    bot.time_frames = [TimeFrames.ONE_MINUTE]
    await bot.create_exchange_traders(ignore_config=True)
    bot.create_evaluation_tasks()
    try:
        event_loop.call_later(5, bot.stop_threads)
        await bot.start_tasks()
    except CancelledError:
        # catch CancelledError since bot main loop gather got cancelled
        pass
