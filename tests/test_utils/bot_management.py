#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import asyncio

from octobot_backtesting.errors import MissingTimeFrame
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.tests.test_config import load_test_config

from octobot.api.backtesting import create_independent_backtesting, \
    initialize_and_run_independent_backtesting, stop_independent_backtesting
from octobot.logger import init_logger
from octobot.octobot import OctoBot
from tests.test_utils.config import load_test_tentacles_config


async def create_bot() -> OctoBot:
    return OctoBot(load_test_config())


async def initialize_bot(bot):
    await bot.initialize()


async def run_independent_backtesting(data_files, timeout=10, use_loggers=True, run_on_common_part_only=True,
                                      enable_storage=False):
    independent_backtesting = None
    try:
        config_to_use = load_test_config()
        if use_loggers:
            init_logger()
        independent_backtesting = create_independent_backtesting(config_to_use,
                                                                 load_test_tentacles_config(),
                                                                 data_files,
                                                                 "",
                                                                 run_on_common_part_only=run_on_common_part_only,
                                                                 enable_storage=enable_storage)
        await initialize_and_run_independent_backtesting(independent_backtesting, log_errors=False)
        await independent_backtesting.join_backtesting_updater(timeout)
        return independent_backtesting
    except MissingTimeFrame:
        # ignore this exception: is due to missing of the only required time frame
        return independent_backtesting
    except asyncio.TimeoutError as e:
        get_logger().exception(e, True, f"Timeout after waiting for backtesting for {timeout} seconds.")
        # stop backtesting to prevent zombie tasks
        await stop_independent_backtesting(independent_backtesting)
        raise
    except Exception as e:
        get_logger().exception(e, True, str(e))
        # stop backtesting to prevent zombie tasks
        await stop_independent_backtesting(independent_backtesting)
        raise
