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
import copy
import time
import aiohttp

from octobot.evaluator_factory import EvaluatorFactory
from octobot.exchange_factory import ExchangeFactory
from octobot.initializer import Initializer
from octobot.task_manager import TaskManager
from octobot_commons.logging.logging_util import get_logger

"""Main OctoBot class:
- Create all indicators and thread for each cryptocurrencies in config """


class OctoBot:
    """
    Constructor :
    - Load configs
    """

    def __init__(self, config, ignore_config=False, reset_trading_history=False):
        self.start_time = time.time()
        self.config = config
        self.reset_trading_history = reset_trading_history
        self.startup_config = copy.deepcopy(config)
        self.edited_config = copy.deepcopy(config)

        # tools: used for alternative operations on a bot on the fly (ex: backtesting started from web interface)
        # self.tools = {
        #     BOT_TOOLS_BACKTESTING: None,
        #     BOT_TOOLS_STRATEGY_OPTIMIZER: None,
        #     BOT_TOOLS_RECORDER: None,
        # }

        # unique aiohttp session: to be initialized from getter in a task
        self._aiohttp_session = None

        # metrics if enabled
        self.metrics_handler = None

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.initializer = Initializer(self)
        self.task_manager = TaskManager(self)
        self.exchange_factory = ExchangeFactory(self, ignore_config=ignore_config)
        self.evaluator_factory = EvaluatorFactory(self)

        self.async_loop = None

    async def initialize(self):
        await self.initializer.create()
        self.task_manager.init_async_loop()
        await self.task_manager.start_tools_tasks()
        await self.evaluator_factory.initialize()
        await self.exchange_factory.create()
        await self.evaluator_factory.create()

    def run_in_main_asyncio_loop(self, coroutine):
        return self.task_manager.run_in_main_asyncio_loop(coroutine)

    def set_watcher(self, watcher):
        self.task_manager.watcher = watcher

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
