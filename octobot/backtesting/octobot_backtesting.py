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
import json
import uuid
import gc
import sys
import asyncio
import time

import octobot_commons.logging as commons_logging
import octobot_commons.configuration as commons_configuration
import octobot_commons.databases as commons_databases
import octobot_commons.constants as commons_constants

import octobot_backtesting.api as backtesting_api
import octobot_backtesting.importers as importers

import octobot_evaluators.api as evaluator_api
import octobot_evaluators.constants as evaluator_constants

import octobot_services.api as service_api

import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_data as exchange_data
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums

import octobot.logger as logger
import octobot.storage as storage
import octobot.databases_util as databases_util


class OctoBotBacktesting:

    def __init__(self, backtesting_config,
                 tentacles_setup_config,
                 symbols_to_create_exchange_classes,
                 backtesting_files,
                 run_on_common_part_only,
                 start_timestamp=None,
                 end_timestamp=None,
                 enable_logs=True,
                 enable_storage=True,
                 run_on_all_available_time_frames=False,
                 backtesting_data=None):
        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.backtesting_config = backtesting_config
        self.tentacles_setup_config = tentacles_setup_config
        self.bot_id = str(uuid.uuid4())
        self.matrix_id = ""
        self.exchange_manager_ids = []
        self.symbols_to_create_exchange_classes = symbols_to_create_exchange_classes
        self.evaluators = []
        self.service_feeds = []
        self.backtesting_files = backtesting_files
        self.backtesting_data = backtesting_data
        if self.backtesting_data is not None:
            self.backtesting_files = [
                backtesting_file
                for backtesting_file in self.backtesting_data.data_files
            ]
        self.backtesting = None
        self.run_on_common_part_only = run_on_common_part_only
        self.start_time = None
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.enable_logs = enable_logs
        self.exchange_type_by_exchange = {}
        self.futures_contract_type = trading_enums.FutureContractType.LINEAR_PERPETUAL
        self.enable_storage = enable_storage
        self.run_on_all_available_time_frames = run_on_all_available_time_frames

    async def initialize_and_run(self):
        self.logger.info(f"Starting on {self.backtesting_files} with {self.symbols_to_create_exchange_classes}")
        self.start_time = time.time()
        await commons_databases.init_bot_storage(
            self.bot_id,
            databases_util.get_run_databases_identifier(
                self.backtesting_config,
                self.tentacles_setup_config,
                enable_storage=self.enable_storage,
            ),
            False
        )
        await self._init_matrix()
        await self._init_backtesting()
        await self._init_evaluators()
        await self._init_service_feeds()
        await self._init_exchanges()
        await self._create_evaluators()
        await self._create_service_feeds()
        await backtesting_api.start_backtesting(self.backtesting)
        if logger.BOT_CHANNEL_LOGGER is not None and self.enable_logs:
            await self.start_loggers()

    async def stop_importers(self):
        if self.backtesting is not None:
            # Close databases
            for importer in backtesting_api.get_importers(self.backtesting):
                if importer is not None:
                    await backtesting_api.stop_importer(importer)

    async def stop(self, memory_check=False, should_raise=False):
        symbols_by_exchange = {
            exchange: [str(s) for s in symbols]
            for exchange, symbols in self.symbols_to_create_exchange_classes.items()
        }
        self.logger.info(f"Stopping for {self.backtesting_files} with {symbols_by_exchange}")
        exchange_managers = []
        try:
            if self.backtesting is None:
                self.logger.warning("No backtesting to stop, there was probably an issue when starting the backtesting")
            else:
                exchange_managers = trading_api.get_exchange_managers_from_exchange_ids(self.exchange_manager_ids)
                if exchange_managers and self.enable_storage:
                    try:
                        for exchange_manager in exchange_managers:
                            await trading_api.store_history_in_run_storage(exchange_manager)
                    except Exception as e:
                        self.logger.exception(e, True, f"Error when saving exchange historical data: {e}")
                    try:
                        await self._store_metadata(exchange_managers)
                        self.logger.info(f"Stored backtesting run metadata")
                    except Exception as e:
                        self.logger.exception(e, True, f"Error when saving run metadata: {e}")
                await backtesting_api.stop_backtesting(self.backtesting)
            try:
                for exchange_manager in exchange_managers:
                    await trading_api.stop_exchange(exchange_manager)
            except KeyError:
                # exchange managers are not added in global exchange list when an exception occurred
                pass
            # close run databases
            await commons_databases.close_bot_storage(self.bot_id)
            # stop evaluators
            for evaluators in self.evaluators:
                # evaluators by type
                for evaluator in evaluators:
                    # evaluator instance
                    if evaluator is not None:
                        await evaluator_api.stop_evaluator(evaluator)
            # close all caches (if caches have to be used later on, they can always be re-opened)
            await commons_databases.CacheManager().close_cache(commons_constants.UNPROVIDED_CACHE_IDENTIFIER)
            try:
                await evaluator_api.stop_all_evaluator_channels(self.matrix_id)
            except KeyError:
                if self.evaluators:
                    raise
                # matrix not created (and no evaluator, KeyError is expected)
            evaluator_api.del_evaluator_channels(self.matrix_id)
            evaluator_api.del_matrix(self.matrix_id)
            for service_feed in self.service_feeds:
                await service_api.stop_service_feed(service_feed)
        except Exception as e:
            self.logger.exception(e, True, f"Error when stopping independent backtesting: {e}")
            if should_raise:
                raise
        finally:
            # call stop_importers in case it has not been called already
            if self.backtesting_data is None:
                await self.stop_importers()

            if memory_check:
                to_reference_check = exchange_managers + [self.backtesting]
                # Call at the next loop iteration to first let coroutines get cancelled
                # (references to coroutine and caller objects are kept while in async loop)
                asyncio.get_event_loop().call_soon(self.memory_leak_checkup, to_reference_check)
            self.backtesting = None

    def memory_leak_checkup(self, to_check_elements):
        self.logger.debug(f"Memory leak checking {[e.__class__.__name__ for e in to_check_elements]}")
        memory_leak_errors = []
        for i in range(len(to_check_elements)):
            if sys.getrefcount(to_check_elements[i]) > 2:
                # Using PyCharm debugger, right click on the element variable and use "Find references"
                # Warning: Python debugger can add references when watching an element
                element = to_check_elements[i]
                # Now expect 3 references because the above element variable adds a reference
                memory_leak_errors.append(f" Too many remaining references on the {element.__class__.__name__} element "
                                          f"after {self.__class__.__name__} run, the garbage collector won't free it "
                                          f"(expected a maximum of 3 references): {sys.getrefcount(element)} actual "
                                          f"references ({element})")
        if memory_leak_errors:
            errors = "\n".join(memory_leak_errors)
            raise AssertionError(
                f"[Dev oriented error: no effect on backtesting result, please report if you see it]: {errors}"
            )

    # Use check_remaining_objects to check remaining objects from garbage collector after calling stop().
    # Warning: can take a long time when a lot of objects exist
    def check_remaining_objects(self):
        objects_leak_errors = []
        exchanges_count = len(self.exchange_manager_ids)
        to_watch_objects = (exchange_data.ExchangeSymbolData, exchanges.ExchangeManager,
                            exchanges.ExchangeSimulator, exchange_data.OHLCVUpdaterSimulator)
        objects_references = {obj: (0, []) for obj in to_watch_objects}
        expected_max_objects_references = {
            exchange_data.ExchangeSymbolData: exchanges_count + 1,
            exchanges.ExchangeManager: exchanges_count + 1,
            exchanges.ExchangeSimulator: exchanges_count,
            exchange_data.OHLCVUpdaterSimulator: exchanges_count
        }
        for obj in gc.get_objects():
            if isinstance(obj, to_watch_objects):
                if isinstance(obj, exchanges.ExchangeManager) and not obj.is_initialized:
                    # Ignore exchange managers that have not been initialized
                    # and are irrelevant. Pytest fixtures can also retain references failing tests
                    continue
                objects_references[type(obj)][1].append(obj)
                objects_references[type(obj)] = (objects_references[type(obj)][0] + 1,
                                                 objects_references[type(obj)][1])

        for obj, max_ref in expected_max_objects_references.items():
            if objects_references[obj][0] > max_ref:
                objects_leak_errors.append(_get_remaining_object_error(obj,
                                                                       max_ref,
                                                                       objects_references[obj]))

        if objects_leak_errors:
            errors = "\n".join(objects_leak_errors)
            raise AssertionError(
                f"[Dev oriented error: no effect on backtesting result, please report if you see it]: {errors}"
            )

    async def _store_metadata(self, exchange_managers):
        run_db = commons_databases.RunDatabasesProvider.instance().get_run_db(self.bot_id)
        await run_db.flush()
        user_inputs = await commons_configuration.get_user_inputs(run_db)
        await storage.store_run_metadata(
            self.bot_id,
            exchange_managers,
            self.start_time,
            user_inputs=user_inputs,
        )
        metadata = await storage.store_backtesting_run_metadata(
            exchange_managers,
            self.start_time,
            user_inputs,
            commons_databases.RunDatabasesProvider.instance().get_run_databases_identifier(self.bot_id),
        )
        self.logger.info(f"Backtesting metadata:\n{json.dumps(metadata, indent=4)}")

    async def _init_matrix(self):
        self.matrix_id = evaluator_api.create_matrix()

    async def _init_evaluators(self):
        await evaluator_api.initialize_evaluators(self.backtesting_config, self.tentacles_setup_config)
        await evaluator_api.create_evaluator_channels(self.matrix_id, is_backtesting=True)

    async def _init_service_feeds(self):
        service_feed_factory = service_api.create_service_feed_factory(self.backtesting_config,
                                                                       asyncio.get_event_loop(),
                                                                       self.bot_id)
        self.service_feeds = [service_feed_factory.create_service_feed(feed)
                              for feed in service_feed_factory.get_available_service_feeds(True)]

    async def _create_evaluators(self):
        for exchange_id in self.exchange_manager_ids:
            exchange_configuration = trading_api.get_exchange_configuration_from_exchange_id(exchange_id)
            self.evaluators = await evaluator_api.create_and_start_all_type_evaluators(
                self.tentacles_setup_config,
                matrix_id=self.matrix_id,
                exchange_name=exchange_configuration.exchange_name,
                bot_id=self.bot_id,
                symbols_by_crypto_currencies=exchange_configuration.symbols_by_crypto_currencies,
                symbols=exchange_configuration.symbols,
                time_frames=exchange_configuration.available_required_time_frames,
                real_time_time_frames=exchange_configuration.real_time_time_frames)

    async def _create_service_feeds(self):
        for feed in self.service_feeds:
            if not await service_api.start_service_feed(feed, False, {}):
                self.logger.error(f"Failed to start {feed.get_name()}. Evaluators requiring this service feed "
                                  f"might not work properly")

    async def _init_backtesting(self):
        if self.backtesting_data:
            self.backtesting_data.reset_cached_indexes()
        self.backtesting = await backtesting_api.initialize_backtesting(
            self.backtesting_config,
            exchange_ids=self.exchange_manager_ids,
            matrix_id=self.matrix_id,
            data_files=self.backtesting_files,
            importers_by_data_file=self.backtesting_data.importers_by_data_file if self.backtesting_data else None,
            backtest_data=self.backtesting_data
        )
        if self.run_on_all_available_time_frames:
            self.backtesting_config[evaluator_constants.CONFIG_FORCED_TIME_FRAME] = [
                tf
                for tf in self.backtesting.importers[0].time_frames
            ]

    async def _init_exchanges(self):
        # modify_backtesting_channels before creating exchanges as they require the current backtesting time to
        # initialize
        await backtesting_api.adapt_backtesting_channels(self.backtesting,
                                                         self.backtesting_config,
                                                         importers.ExchangeDataImporter,
                                                         run_on_common_part_only=self.run_on_common_part_only,
                                                         start_timestamp=self.start_timestamp,
                                                         end_timestamp=self.end_timestamp)

        for exchange_class_string in self.symbols_to_create_exchange_classes.keys():
            is_future = self.exchange_type_by_exchange[exchange_class_string] == \
                        commons_constants.CONFIG_EXCHANGE_FUTURE
            exchange_builder = trading_api.create_exchange_builder(self.backtesting_config, exchange_class_string) \
                .has_matrix(self.matrix_id) \
                .use_tentacles_setup_config(self.tentacles_setup_config) \
                .set_bot_id(self.bot_id) \
                .is_simulated() \
                .is_rest_only() \
                .is_backtesting(self.backtesting) \
                .is_future(is_future, self.futures_contract_type) \
                .enable_storage(self.enable_storage)
            try:
                await exchange_builder.build()
            finally:
                # always save exchange manager ids and backtesting instances
                self.exchange_manager_ids.append(trading_api.get_exchange_manager_id(exchange_builder.exchange_manager))

    async def start_loggers(self):
        await self.start_exchange_loggers()
        await logger.init_evaluator_chan_logger(self.matrix_id)

    async def start_exchange_loggers(self):
        for exchange_manager_id in self.exchange_manager_ids:
            await logger.init_exchange_chan_logger(exchange_manager_id)


def _get_remaining_object_error(obj, expected, actual):
    error = f"too many remaining {obj.__name__} instances: expected: {expected} actual {actual[0]}"
    for i in range(len(actual[1])):
        debug_info = ""
        if isinstance(actual[1][i], exchanges.ExchangeManager):
            debug_info = f" ({actual[1][i].debug_info})"
        error += f"{sys.getrefcount(actual[1][i])} references on {actual[1][i]} {debug_info}"
        return error
