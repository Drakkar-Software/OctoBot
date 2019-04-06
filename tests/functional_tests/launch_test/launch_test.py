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

from config import *
from core.octobot import OctoBot
from tests.test_utils.config import load_test_config
from tests.test_utils.bot_management import call_stop_later, start_bot_with_raise

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
    await bot.initialize()
    await call_stop_later(5, event_loop, bot)
    await start_bot_with_raise(bot)
