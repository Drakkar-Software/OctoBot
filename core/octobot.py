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
import copy
import time
import aiohttp

from config import BOT_TOOLS_RECORDER, BOT_TOOLS_STRATEGY_OPTIMIZER, BOT_TOOLS_BACKTESTING
from core.evaluator_factory import EvaluatorFactory
from core.exchange_factory import ExchangeFactory
from core.initializer import Initializer
from core.task_manager import TaskManager
from tools.logging.logging_util import get_logger

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
        self.tools = {
            BOT_TOOLS_BACKTESTING: None,
            BOT_TOOLS_STRATEGY_OPTIMIZER: None,
            BOT_TOOLS_RECORDER: None,
        }

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

    async def initialize(self):
        await self.initializer.create()
        self.task_manager.init_async_loop()
        await self.exchange_factory.create()
        self.evaluator_factory.create()

    async def start(self, run_in_new_thread=False):
        await self.task_manager.start_tasks(run_in_new_thread=run_in_new_thread)

    def stop(self):
        self.task_manager.stop_threads()

    def run_in_main_asyncio_loop(self, coroutine):
        return self.task_manager.run_in_main_asyncio_loop(coroutine)

    def set_watcher(self, watcher):
        self.task_manager.watcher = watcher

    def get_symbols_tasks_manager(self):
        return self.evaluator_factory.symbol_tasks_manager

    def get_exchange_traders(self):
        return self.exchange_factory.exchange_traders

    def get_exchange_trader_simulators(self):
        return self.exchange_factory.exchange_trader_simulators

    def get_exchange_trading_modes(self):
        return self.exchange_factory.exchange_trading_modes

    def get_exchanges_list(self):
        return self.exchange_factory.exchanges_list

    def get_symbol_evaluator_list(self):
        return self.evaluator_factory.symbol_evaluator_list

    def get_symbols_list(self):
        return self.evaluator_factory.symbol_evaluator_list.keys()

    def get_crypto_currency_evaluator_list(self):
        return self.evaluator_factory.crypto_currency_evaluator_list

    def get_dispatchers_list(self):
        return self.evaluator_factory.dispatchers_list

    def get_global_updaters_by_exchange(self):
        return self.exchange_factory.global_updaters_by_exchange

    def get_trading_mode(self):
        return self.exchange_factory.trading_mode

    def is_ready(self):
        return self.task_manager.ready

    def get_config(self):
        return self.config

    def get_tools(self):
        return self.tools

    def get_time_frames(self):
        return self.initializer.time_frames

    def get_relevant_evaluators(self):
        return self.initializer.relevant_evaluators

    def get_async_loop(self):
        return self.task_manager.async_loop

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
