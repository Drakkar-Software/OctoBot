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
from threading import Thread

import pytest

from backtesting.backtesting_util import start_bot
from core.octobot import OctoBot
from tests.test_utils.config import load_test_config


def stop_bot(bot):
    thread = Thread(target=bot.stop)
    thread.start()
    thread.join()


async def create_bot() -> OctoBot:
    # launch a bot
    config = load_test_config()
    return OctoBot(config)


async def initialize_bot(bot):
    await bot.initialize()


async def call_stop_later(time, event_loop, bot):
    event_loop.call_later(time, stop_bot, bot)


async def start_bot_with_raise(bot, run_in_new_thread=False):
    with pytest.raises(CancelledError):
        await start_bot(bot, run_in_new_thread)
