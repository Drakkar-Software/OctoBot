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

from tentacles.Services.Interfaces.web_interface import WebInterface
from octobot_commons.tests.test_config import load_test_config
from octobot.commands import start_bot
from octobot.logger import init_logger
from octobot.octobot import OctoBot

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_run_bot():
    # avoid web interface in this test
    WebInterface.enabled = False
    bot = OctoBot(load_test_config(), ignore_config=True)
    bot.task_manager.init_async_loop()
    await start_bot(bot, init_logger())
    await asyncio.sleep(10)
    bot.task_manager.stop_tasks()
