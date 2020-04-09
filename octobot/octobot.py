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
import time
import uuid

import aiohttp

from octobot.constants import PROJECT_NAME, LONG_VERSION, CONFIG_KEY, TENTACLES_SETUP_CONFIG_KEY
from octobot.configuration_manager import ConfigurationManager
from octobot.factories.evaluator_factory import EvaluatorFactory
from octobot.factories.exchange_factory import ExchangeFactory
from octobot.octobot_api import OctoBotAPI
from octobot.factories.service_feed_factory import ServiceFeedFactory
from octobot.initializer import Initializer
from octobot.factories.interface_factory import InterfaceFactory
from octobot.task_manager import TaskManager
from octobot_commons.enums import MarkdownFormat
from octobot_commons.logging.logging_util import get_logger
from octobot_notifications.api.notification import send_notification, create_notification
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id
from octobot_trading.api.modes import get_trading_modes

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

        # tentacle setup configuration
        self.tentacles_setup_config = None

        # Configuration manager to handle current, edited and startup configurations
        self.configuration_manager = ConfigurationManager()
        self.configuration_manager.add_element(CONFIG_KEY, self.config)

        # Used to know when OctoBot is ready to answer in APIs
        self.initialized = False

        # tools: used for alternative operations on a bot on the fly (ex: backtesting started from web interface)
        # self.tools = {
        #     BOT_TOOLS_BACKTESTING: None,
        #     BOT_TOOLS_STRATEGY_OPTIMIZER: None,
        #     BOT_TOOLS_RECORDER: None,
        # }

        # unique aiohttp session: to be initialized from getter in a task
        self._aiohttp_session = None

        # community if enabled
        self.community_handler = None

        # octobot_api to request the current instance
        self.octobot_api = OctoBotAPI(self)

        # octobot instance id
        self.bot_id = str(uuid.uuid4())

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.initializer = Initializer(self)
        self.task_manager = TaskManager(self)
        self.exchange_factory = ExchangeFactory(self, ignore_config=ignore_config)
        self.evaluator_factory = EvaluatorFactory(self)
        self.interface_factory = InterfaceFactory(self)
        self.service_feed_factory = ServiceFeedFactory(self)

        self.async_loop = None

    async def initialize(self):
        await self.initializer.create()
        self.task_manager.init_async_loop()
        await self.task_manager.start_tools_tasks()
        await self.evaluator_factory.initialize()
        await self.service_feed_factory.initialize()
        await self.exchange_factory.create()
        await self.evaluator_factory.create()
        # Start service feeds now that evaluators registered their feed requirements
        await self.service_feed_factory.create()
        await self.interface_factory.create()
        await self.interface_factory.start_interfaces()
        await self._post_initialize()

    async def _post_initialize(self):
        self.initialized = True

        # make tentacles setup config editable while saving previous states
        self.configuration_manager.add_element(TENTACLES_SETUP_CONFIG_KEY, self.tentacles_setup_config)
        await send_notification(create_notification(f"{PROJECT_NAME} {LONG_VERSION} is starting ...",
                                                    markdown_format=MarkdownFormat.ITALIC))

    def get_edited_config(self, config_key):
        return self.configuration_manager.get_edited_config(config_key)

    def get_startup_config(self, config_key):
        return self.configuration_manager.get_startup_config(config_key)

    def get_trading_mode(self):
        first_exchange_manager = get_exchange_manager_from_exchange_id(
            next(iter(self.exchange_factory.exchange_manager_ids))
        )
        return get_trading_modes(first_exchange_manager)[0]

    def run_in_main_asyncio_loop(self, coroutine):
        return self.task_manager.run_in_main_asyncio_loop(coroutine)

    def set_watcher(self, watcher):
        self.task_manager.watcher = watcher

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
