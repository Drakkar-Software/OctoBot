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
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.tests.test_config import load_test_config
from octobot_backtesting.data import MissingTimeFrame
from octobot_tentacles_manager.api.configurator import get_tentacles_setup_config

from octobot.api.backtesting import stop_independent_backtesting, create_independent_backtesting, \
    initialize_and_run_independent_backtesting
from octobot.commands import start_bot, stop_bot
from octobot.logger import init_logger
from octobot.octobot import OctoBot


async def create_bot() -> OctoBot:
    return OctoBot(load_test_config())


async def initialize_bot(bot):
    await bot.initialize()


async def call_stop_later(time, event_loop, bot):
    event_loop.call_later(time, stop_bot, bot)


async def start_bot_with_raise(bot):
    with pytest.raises(CancelledError):
        await start_bot(bot, init_logger())


async def run_independent_backtesting(data_files, timeout=10):
    independent_backtesting = None
    try:
        config_to_use = load_test_config()
        independent_backtesting = create_independent_backtesting(config_to_use,
                                                                 await get_tentacles_setup_config(),
                                                                 data_files,
                                                                 "")
        await initialize_and_run_independent_backtesting(independent_backtesting, log_errors=False)
        await independent_backtesting.join(timeout)
        return independent_backtesting
    except MissingTimeFrame:
        # ignore this exception: is due to missing of the only required time frame
        return independent_backtesting
    except Exception as e:
        get_logger().exception(e, True, str(e))
        return independent_backtesting
