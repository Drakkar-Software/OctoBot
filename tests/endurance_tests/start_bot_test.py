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
import pytest

from config import *
from octobot import OctoBot
from tests.test_utils.config import load_test_config


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_bot():
    # launch a bot
    config = load_test_config()
    bot = OctoBot(config)
    bot.stop_threads()


async def test_run_bot():
    # launch a bot
    config = load_test_config()
    bot = OctoBot(config)
    bot.time_frames = [TimeFrames.ONE_MINUTE]
    await bot.create_exchange_traders()
    bot.create_evaluation_tasks()
    await bot.start_tasks(run_in_new_thread=True, run_forever=False)

    # let it run 2 minutes: test will fail if an exception is raised
    # 1.9 to stop task before the next time frame
    await asyncio.sleep(1.9*60)

    # stop the bot
    bot.stop_threads()
