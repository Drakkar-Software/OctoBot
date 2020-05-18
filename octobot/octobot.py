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

from octobot.logger import init_octobot_chan_logger
from octobot_services.api.services import stop_services

from octobot.community.community_manager import CommunityManager
from octobot.constants import PROJECT_NAME, LONG_VERSION, CONFIG_KEY, TENTACLES_SETUP_CONFIG_KEY
from octobot.configuration_manager import ConfigurationManager
from octobot.consumers.octobot_channel_consumer import OctoBotChannelGlobalConsumer
from octobot.producers.evaluator_producer import EvaluatorProducer
from octobot.api.octobot_api import OctoBotAPI
from octobot.producers.service_feed_producer import ServiceFeedProducer
from octobot.initializer import Initializer
from octobot.producers.interface_producer import InterfaceProducer
from octobot.producers.exchange_producer import ExchangeProducer
from octobot.task_manager import TaskManager
from octobot_commons.enums import MarkdownFormat
from octobot_commons.logging.logging_util import get_logger
from octobot_services.api.notification import send_notification, create_notification
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
        self.ignore_config = ignore_config
        self.reset_trading_history = reset_trading_history

        # tentacle setup configuration
        self.tentacles_setup_config = None

        # Configuration manager to handle current, edited and startup configurations
        self.configuration_manager = ConfigurationManager()
        self.configuration_manager.add_element(CONFIG_KEY, self.config)

        # Used to know when OctoBot is ready to answer in APIs
        self.initialized = False

        # unique aiohttp session: to be initialized from getter in a task
        self._aiohttp_session = None

        # community if enabled
        self.community_handler = None

        # octobot_api to request the current instance
        self.octobot_api = OctoBotAPI(self)

        # octobot channel global consumer
        self.global_consumer = OctoBotChannelGlobalConsumer(self)

        # octobot instance id
        self.bot_id = str(uuid.uuid4())

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        # Initialize octobot main tools
        self.initializer = Initializer(self)
        self.task_manager = TaskManager(self)

        # Producers
        self.exchange_producer = None
        self.evaluator_producer = None
        self.interface_producer = None
        self.service_feed_producer = None

        self.async_loop = None
        self.community_handler = None

    async def initialize(self):
        await self.initializer.create()
        await self.task_manager.start_tools_tasks()
        await init_octobot_chan_logger(self.bot_id)
        await self.create_producers()
        await self.start_producers()

    async def create_producers(self):
        self.exchange_producer = ExchangeProducer(self.global_consumer.octobot_channel, self,
                                                  None, self.ignore_config)
        self.evaluator_producer = EvaluatorProducer(self.global_consumer.octobot_channel, self)
        self.interface_producer = InterfaceProducer(self.global_consumer.octobot_channel, self)
        self.service_feed_producer = ServiceFeedProducer(self.global_consumer.octobot_channel, self)

    async def start_producers(self):
        await self.evaluator_producer.run()
        await self.exchange_producer.run()
        # Start service feeds now that evaluators registered their feed requirements
        await self.service_feed_producer.run()
        await self.interface_producer.run()
        await self._post_initialize()

    async def _post_initialize(self):
        self.initialized = True

        # make tentacles setup config editable while saving previous states
        self.configuration_manager.add_element(TENTACLES_SETUP_CONFIG_KEY, self.tentacles_setup_config)
        await send_notification(create_notification(f"{PROJECT_NAME} {LONG_VERSION} is starting ...",
                                                    markdown_format=MarkdownFormat.ITALIC))

        # initialize tools
        self._init_community()

    async def stop(self):
        await self.service_feed_producer.stop()
        stop_services()
        await self.interface_producer.stop()
        self.logger.info("Shutting down.")

    def _init_community(self):
        self.community_handler = CommunityManager(self.octobot_api)

    def get_edited_config(self, config_key):
        return self.configuration_manager.get_edited_config(config_key)

    def get_startup_config(self, config_key):
        return self.configuration_manager.get_startup_config(config_key)

    def get_trading_mode(self):
        try:
            first_exchange_manager = get_exchange_manager_from_exchange_id(
                next(iter(self.exchange_producer.exchange_manager_ids))
            )
            return get_trading_modes(first_exchange_manager)[0]
        except StopIteration:
            return None

    def run_in_main_asyncio_loop(self, coroutine):
        return self.task_manager.run_in_main_asyncio_loop(coroutine)

    def set_watcher(self, watcher):
        self.task_manager.watcher = watcher

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
