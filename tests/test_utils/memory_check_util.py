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

from octobot.api.backtesting import create_independent_backtesting, initialize_and_run_independent_backtesting, \
    check_independent_backtesting_remaining_objects, stop_independent_backtesting, join_independent_backtesting
from octobot.backtesting.abstract_backtesting_test import DATA_FILES
from octobot_commons.asyncio_tools import ErrorContainer


async def run_independent_backtestings_with_memory_check(config, tentacles_setup_config, backtesting_count=3):
    """
    Will raise an error of an object is not deleted by garbage collector at the end of the backtesting process
    :param config: the global config to use in backtesting
    :param tentacles_setup_config: the tentacles setup config to use (with the tentacles to be tested)
    :param backtesting_count: number of backtestings to run to ensure no side effects, default is 3
    :return:
    """
    for _ in range(backtesting_count):
        error_container = ErrorContainer()
        asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
        backtesting = await _run_backtesting(config, tentacles_setup_config)
        await stop_independent_backtesting(backtesting, memory_check=True)
        asyncio.get_event_loop().call_soon(check_independent_backtesting_remaining_objects, backtesting)
        await asyncio.create_task(error_container.check())


async def _run_backtesting(config, tentacles_setup_config):
    backtesting = create_independent_backtesting(config, tentacles_setup_config, [DATA_FILES["ETH/USDT"]], "")
    await initialize_and_run_independent_backtesting(backtesting, log_errors=False)
    await join_independent_backtesting(backtesting)
    return backtesting
