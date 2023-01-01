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

import octobot_commons.constants as commons_constants
from octobot.api.backtesting import create_independent_backtesting, initialize_and_run_independent_backtesting, \
    check_independent_backtesting_remaining_objects, stop_independent_backtesting, join_independent_backtesting, \
    get_independent_backtesting_exchange_manager_ids
from octobot.backtesting.abstract_backtesting_test import DATA_FILES
from octobot_commons.asyncio_tools import ErrorContainer
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id
from octobot_trading.api.orders import get_open_orders
from octobot_trading.api.trades import get_trade_history


async def run_independent_backtestings_with_memory_check(config, tentacles_setup_config, backtesting_count=3):
    """
    Will raise an error of an object is not deleted by garbage collector at the end of the backtesting process
    :param config: the global config to use in backtesting
    :param tentacles_setup_config: the tentacles setup config to use (with the tentacles to be tested)
    :param backtesting_count: number of backtestings to run to ensure no side effects, default is 3
    :return:
    """
    backtesting = None
    try:
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 10000
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["ETH"] = 20
        for _ in range(backtesting_count):
            error_container = ErrorContainer()
            asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
            # enabling loggers is slowing down backtesting but can display useful debug info
            # from octobot.logger import init_logger
            # init_logger()
            backtesting = await _run_backtesting(config, tentacles_setup_config)
            exchange_manager = get_exchange_manager_from_exchange_id(
                get_independent_backtesting_exchange_manager_ids(backtesting)[0])
            trades = get_trade_history(exchange_manager)
            open_orders = get_open_orders(exchange_manager)
            # ensure at least one order is either open or got filled
            assert trades + open_orders
            trades = open_orders = exchange_manager = None  # prevent memory leak
            await stop_independent_backtesting(backtesting, memory_check=True)
            await asyncio.wait_for(backtesting.post_backtesting_task, 5)
            asyncio.get_event_loop().call_soon(check_independent_backtesting_remaining_objects, backtesting)
            await asyncio.create_task(error_container.check())
    except Exception as e:
        if backtesting is not None:
            # do not get stuck in running backtesting
            await stop_independent_backtesting(backtesting, memory_check=False)
            await asyncio.wait_for(backtesting.post_backtesting_task, 5)
        raise e


async def _run_backtesting(config, tentacles_setup_config):
    backtesting = create_independent_backtesting(config, tentacles_setup_config, [DATA_FILES["ETH/USDT"]], "",
                                                 enable_storage=False)
    await initialize_and_run_independent_backtesting(backtesting, log_errors=False)
    await join_independent_backtesting(backtesting)
    return backtesting
