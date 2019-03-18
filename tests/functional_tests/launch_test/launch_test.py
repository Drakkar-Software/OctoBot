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

import pytest
import asyncio

from config import *
from core.octobot import OctoBot
from tests.test_utils.config import load_test_config


from tools.errors import TentacleNotFound

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
    bot = OctoBot(config, ignore_config=True)
    bot.time_frames = [TimeFrames.ONE_MINUTE]
    try:
        await bot.initialize()
    except TentacleNotFound:
        pass
    await bot.start()
    await asyncio.sleep(5)
    await asyncio.get_event_loop().run_in_executor(None, bot.stop)
