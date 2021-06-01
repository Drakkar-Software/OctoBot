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

import octobot_commons.enums as enums
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration

import octobot_services.api as service_api
import octobot_trading.api as trading_api

import octobot.logger as logger
import octobot.community as community_manager
import octobot.constants as constants
import octobot.configuration_manager as configuration_manager
import octobot.task_manager as task_manager
import octobot.octobot_channel_consumer as octobot_channel_consumer
import octobot.octobot_api as octobot_api
import octobot.initializer as initializer
import octobot.producers as producers

"""Main OctoBot class:
- Create all indicators and thread for each cryptocurrencies in config """


class OctoBot:
    """
    Constructor :
    - Load configs
    """

    def __init__(self, config: configuration.Configuration, ignore_config=False, reset_trading_history=False):
        self.start_time = time.time()
        self.config = config.config
        self.ignore_config = ignore_config
        self.reset_trading_history = reset_trading_history

        # tentacle setup configuration
        self.tentacles_setup_config = None

        # Configuration manager to handle current, edited and startup configurations
        self.configuration_manager = configuration_manager.ConfigurationManager()
        self.configuration_manager.add_element(constants.CONFIG_KEY, config, has_dict=True)

        # Used to know when OctoBot is ready to answer in APIs
        self.initialized = False

        # unique aiohttp session: to be initialized from getter in a task
        self._aiohttp_session = None

        # community if enabled
        self.community_handler = None

        # community authentication
        self.community_auth = community_manager.CommunityAuthentication(
            constants.OCTOBOT_COMMUNITY_AUTH_URL,
            config=self.get_edited_config(constants.CONFIG_KEY, dict_only=False),
        )

        # octobot_api to request the current instance
        self.octobot_api = octobot_api.OctoBotAPI(self)

        # octobot channel global consumer
        self.global_consumer = octobot_channel_consumer.OctoBotChannelGlobalConsumer(self)

        # octobot instance id
        self.bot_id = str(uuid.uuid4())

        # Logger
        self.logger = logging.get_logger(self.__class__.__name__)

        # Initialize octobot main tools
        self.initializer = initializer.Initializer(self)
        self.task_manager = task_manager.TaskManager(self)

        # Producers
        self.exchange_producer = None
        self.evaluator_producer = None
        self.interface_producer = None
        self.service_feed_producer = None

        self.async_loop = None

    async def initialize(self):
        await self.initializer.create()
        await self._start_tools_tasks()
        await logger.init_octobot_chan_logger(self.bot_id)
        await self.create_producers()
        await self.start_producers()

    async def create_producers(self):
        self.exchange_producer = producers.ExchangeProducer(self.global_consumer.octobot_channel, self,
                                                            None, self.ignore_config)
        self.evaluator_producer = producers.EvaluatorProducer(self.global_consumer.octobot_channel, self)
        self.interface_producer = producers.InterfaceProducer(self.global_consumer.octobot_channel, self)
        self.service_feed_producer = producers.ServiceFeedProducer(self.global_consumer.octobot_channel, self)

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
        self.configuration_manager.add_element(constants.TENTACLES_SETUP_CONFIG_KEY, self.tentacles_setup_config)
        await service_api.send_notification(
            service_api.create_notification(f"{constants.PROJECT_NAME} {constants.LONG_VERSION} is starting ...",
                                            markdown_format=enums.MarkdownFormat.ITALIC))

    async def stop(self):
        await self.exchange_producer.stop()
        await self.service_feed_producer.stop()
        service_api.stop_services()
        await self.interface_producer.stop()
        await self.community_auth.stop()
        self.logger.info("Shutting down.")

    async def _start_tools_tasks(self):
        self._init_community()
        await self.task_manager.start_tools_tasks()

    def _init_community(self):
        self.community_handler = community_manager.CommunityManager(self.octobot_api)

    def get_edited_config(self, config_key, dict_only=True):
        return self.configuration_manager.get_edited_config(config_key, dict_only)

    def set_edited_config(self, config_key, config):
        self.configuration_manager.set_edited_config(config_key, config)

    def get_startup_config(self, config_key, dict_only=True):
        return self.configuration_manager.get_startup_config(config_key, dict_only)

    def get_trading_mode(self):
        try:
            first_exchange_manager = trading_api.get_exchange_manager_from_exchange_id(
                next(iter(self.exchange_producer.exchange_manager_ids))
            )
            return trading_api.get_trading_modes(first_exchange_manager)[0]
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
