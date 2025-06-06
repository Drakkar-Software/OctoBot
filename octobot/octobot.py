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
import time
import uuid

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration
import octobot_commons.signals as signals
import octobot_commons.databases as databases
import octobot_commons.tree as commons_tree
import octobot_commons.os_clock_sync as os_clock_sync
import octobot_commons.system_resources_watcher as system_resources_watcher
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.profiles as profiles
import octobot_commons.errors

import octobot_services.api as service_api
import octobot_trading.api as trading_api

import octobot.logger as logger
import octobot.community as community
import octobot.constants as constants
import octobot.configuration_manager as configuration_manager
import octobot.task_manager as task_manager
import octobot.octobot_channel_consumer as octobot_channel_consumer
import octobot.octobot_api as octobot_api
import octobot.initializer as initializer
import octobot.producers as producers
import octobot.storage as storage
import octobot.automation as automation

"""Main OctoBot class:
- Create all indicators and thread for each cryptocurrencies in config """


class OctoBot:
    """
    Constructor :
    - Load configs
    """

    def __init__(self, config: configuration.Configuration, community_authenticator=None,
                 ignore_config=False, reset_trading_history=False, startup_messages=None):
        self.start_time = time.time()
        self.config = config.config
        self.ignore_config = ignore_config
        self.reset_trading_history = reset_trading_history
        self.startup_messages = startup_messages

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

        # use edited config in community authentication
        community_config = self.get_edited_config(constants.CONFIG_KEY, dict_only=False)
        self.community_auth = community_authenticator or community.CommunityAuthentication.create(community_config)
        self.community_auth.update(community_config)

        # octobot_api to request the current instance
        self.octobot_api = octobot_api.OctoBotAPI(self)

        # octobot channel global consumer
        self.global_consumer = octobot_channel_consumer.OctoBotChannelGlobalConsumer(self)

        # octobot instance id
        self.bot_id = str(uuid.uuid4())

        # Logger
        self.logger = logging.get_logger(self.__class__.__name__)

        # automations
        self.automation = None

        # Initialize octobot main tools
        self.initializer = initializer.Initializer(self)
        self.task_manager = task_manager.TaskManager(self)
        self._init_metadata_run_task = None

        # Producers
        self.exchange_producer = None
        self.evaluator_producer = None
        self.interface_producer = None
        self.service_feed_producer = None

        self.async_loop = None
        self.stopped = None

    async def initialize(self):
        self.stopped = asyncio.Event()
        await self._ensure_clock()
        if not (self.community_auth.is_initialized() and self.community_auth.is_using_the_current_loop()):
            self.community_auth.init_account(True)
        await self.initializer.create(True)
        self._log_config()
        await self._start_tools_tasks()
        await logger.init_octobot_chan_logger(self.bot_id)
        await self.create_producers()
        await self.start_producers()
        await self._ensure_watchers()
        await self._post_initialize()

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

    async def _post_initialize(self):
        self.initialized = True

        # make tentacles setup config editable while saving previous states
        self.configuration_manager.add_element(constants.TENTACLES_SETUP_CONFIG_KEY, self.tentacles_setup_config)
        await service_api.send_notification(
            service_api.create_notification(f"{constants.PROJECT_NAME} {constants.LONG_VERSION} is starting ...",
                                            markdown_format=commons_enums.MarkdownFormat.ITALIC)
        )
        if self.startup_messages:
            for limit_message in self.startup_messages:
                self.logger.info(f"Startup message: {limit_message}")
                await service_api.send_notification(
                    service_api.create_notification(limit_message)
                )

        self.automation = automation.Automation(self.bot_id, self.tentacles_setup_config)
        self._init_metadata_run_task = asyncio.create_task(self._store_run_metadata_when_available())
        await self._init_profile_synchronizer()

    async def _wait_for_run_data_init(self, exchange_managers, timeout):
        for exchange_manager in exchange_managers:
            for topic in constants.REQUIRED_TOPIC_FOR_DATA_INIT:
                await commons_tree.EventProvider.instance().wait_for_event(
                    self.bot_id,
                    commons_tree.get_exchange_path(
                        trading_api.get_exchange_name(exchange_manager),
                        topic.value
                    ),
                    timeout
                )

    async def _store_run_metadata_when_available(self):
        run_metadata_init_timeout = 5 * commons_constants.MINUTE_TO_SECONDS
        # first wait for all exchanges to be created
        try:
            await asyncio.wait_for(self.exchange_producer.created_all_exchanges.wait(), run_metadata_init_timeout)
        except asyncio.TimeoutError:
            pass
        exchange_managers = [
            trading_api.get_exchange_manager_from_exchange_id(exchange_manager_id)
            for exchange_manager_id in self.exchange_producer.exchange_manager_ids
            if trading_api.is_trader_existing_and_enabled(
                trading_api.get_exchange_manager_from_exchange_id(exchange_manager_id)
            )
        ]
        # start automations now that everything started
        await self.automation.initialize()
        try:
            await self._wait_for_run_data_init(exchange_managers, run_metadata_init_timeout)
        except asyncio.TimeoutError:
            pass
        try:
            if exchange_managers:
                await storage.clear_run_metadata(self.bot_id)
                await storage.store_run_metadata(self.bot_id, exchange_managers, self.start_time, flush=True)
            else:
                self.logger.debug("Skipping run metadata update: no available exchange manager")
        except Exception as err:
            self.logger.exception(err, True, f"Error when storing live metadata: {err}")

    async def stop(self):
        try:
            self.logger.debug("Stopping ...")
            if self._init_metadata_run_task is not None and not self._init_metadata_run_task.done():
                self._init_metadata_run_task.cancel()
            signals.SignalPublisher.instance().stop()
            await self.evaluator_producer.stop()
            await self.exchange_producer.stop()
            await self.community_auth.stop()
            await self.service_feed_producer.stop()
            await profiles.stop_profile_synchronizer()
            await os_clock_sync.stop_clock_synchronizer()
            await system_resources_watcher.stop_system_resources_watcher()
            await service_api.stop_services()
            await self.interface_producer.stop()
            await databases.close_bot_storage(self.bot_id)
            if self.automation is not None:
                await self.automation.stop()

        finally:
            self.stopped.set()
            self.logger.info("Stopped, now shutting down.")

    async def _start_tools_tasks(self):
        await self._init_aiohttp_session()
        self._init_community()
        await self.task_manager.start_tools_tasks()

    def _init_community(self):
        self.community_handler = community.CommunityManager(self.octobot_api)

    async def _ensure_clock(self):
        if trading_api.is_trader_enabled_in_config(self.config) and constants.ENABLE_CLOCK_SYNCH:
            await os_clock_sync.start_clock_synchronizer()

    async def _init_profile_synchronizer(self):
        await profiles.start_profile_synchronizer(
            self.get_edited_config(constants.CONFIG_KEY, dict_only=False),
            self._on_profile_update
        )

    async def delayed_restart(self, delay):
        await asyncio.sleep(delay)
        self.octobot_api.restart_bot()

    async def _on_profile_update(self, profile_name: str):
        await service_api.send_notification(
            service_api.create_notification(
                f"{constants.PROJECT_NAME} will restart in {constants.PROFILE_UPDATE_RESTART_MIN} minutes "
                f"to apply the {profile_name} profile update.",
                markdown_format=commons_enums.MarkdownFormat.ITALIC
            )
        )
        asyncio.create_task(self.delayed_restart(
            constants.PROFILE_UPDATE_RESTART_MIN * commons_constants.MINUTE_TO_SECONDS
        ))

    async def _ensure_watchers(self):
        if constants.ENABLE_SYSTEM_WATCHER:
            await system_resources_watcher.start_system_resources_watcher(
                constants.DUMP_USED_RESOURCES,
                constants.WATCH_RAM,
                constants.USED_RESOURCES_OUTPUT
            )

    def _log_config(self):
        exchanges = [
            f"{exchange}" \
            f"[{config.get(commons_constants.CONFIG_EXCHANGE_TYPE, trading_api.get_default_exchange_type(exchange))}]"
            for exchange, config in self.config.get(commons_constants.CONFIG_EXCHANGES, {}).items()
            if config.get(commons_constants.CONFIG_ENABLED_OPTION, True)
        ]
        has_real_trader = trading_api.is_trader_enabled_in_config(self.config)
        has_simulated_trader = trading_api.is_trader_simulator_enabled_in_config(self.config)
        trader_str = "real trader" if has_real_trader else "simulated trader" if has_simulated_trader else "no trader"
        traded_symbols = trading_api.get_config_symbols(self.config, True)
        symbols_str = ', '.join(set(traded_symbols))
        trading_mode = None
        try:
            trading_mode = trading_api.get_activated_trading_mode(self.tentacles_setup_config)
        except octobot_commons.errors.ConfigTradingError as err:
            # no active trading mode
            self.logger.warning(f"Failed to get activated trading mode: {err}" )
        trading_mode_str = trading_mode.get_name() if trading_mode else "no trading mode"
        self.logger.info(f"Starting OctoBot with {trader_str} on "
                         f"{', '.join(exchanges) if exchanges else 'no exchange'} "
                         f"trading {symbols_str or 'nothing'} with {trading_mode_str} and using bot_id: {self.bot_id}")

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
        except (StopIteration, IndexError):
            return None

    def run_in_main_asyncio_loop(self, coroutine, log_exceptions=True,
                                 timeout=commons_constants.DEFAULT_FUTURE_TIMEOUT):
        return self.task_manager.run_in_main_asyncio_loop(coroutine, log_exceptions=log_exceptions, timeout=timeout)

    def set_watcher(self, watcher):
        self.task_manager.watcher = watcher

    async def _init_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = await aiohttp_util.get_ssl_fallback_aiohttp_client_session(
                commons_constants.KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL
            )

    def get_aiohttp_session(self):
        return self._aiohttp_session
