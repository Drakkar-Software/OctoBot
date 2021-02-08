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
import uuid
import gc
import sys
import asyncio

import octobot_commons.logging as logging

import octobot_backtesting.api as backtesting_api
import octobot_backtesting.importers as importers

import octobot_evaluators.api as evaluator_api

import octobot_services.api as service_api

import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_data as exchange_data
import octobot_trading.api as trading_api

import octobot.logger as logger


class OctoBotBacktesting:

    def __init__(self, backtesting_config,
                 tentacles_setup_config,
                 symbols_to_create_exchange_classes,
                 backtesting_files,
                 run_on_common_part_only):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.backtesting_config = backtesting_config
        self.tentacles_setup_config = tentacles_setup_config
        self.bot_id = str(uuid.uuid4())
        self.matrix_id = ""
        self.exchange_manager_ids = []
        self.symbols_to_create_exchange_classes = symbols_to_create_exchange_classes
        self.evaluators = []
        self.service_feeds = []
        self.backtesting_files = backtesting_files
        self.backtesting = None
        self.run_on_common_part_only = run_on_common_part_only

    async def initialize_and_run(self):
        self.logger.info(f"Starting on {self.backtesting_files} with {self.symbols_to_create_exchange_classes}")
        await self._init_evaluators()
        await self._init_service_feeds()
        await self._init_exchanges()
        await self._create_evaluators()
        await self._create_service_feeds()
        await backtesting_api.start_backtesting(self.backtesting)
        if logger.BOT_CHANNEL_LOGGER is not None:
            await self.start_loggers()

    async def stop_importers(self):
        if self.backtesting is not None:
            # Close databases
            for importer in backtesting_api.get_importers(self.backtesting):
                if importer is not None:
                    await backtesting_api.stop_importer(importer)

    async def stop(self, memory_check=False, should_raise=False):
        self.logger.info(f"Stopping for {self.backtesting_files} with {self.symbols_to_create_exchange_classes}")
        try:
            await backtesting_api.stop_backtesting(self.backtesting)
            exchange_managers = []
            try:
                for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(self.exchange_manager_ids):
                    exchange_managers.append(exchange_manager)
                    await trading_api.stop_exchange(exchange_manager)
            except KeyError:
                # exchange managers are not added in global exchange list when an exception occurred
                pass
            for evaluators in self.evaluators:
                # evaluators by type
                for evaluator in evaluators:
                    # evaluator instance
                    if evaluator is not None:
                        await evaluator_api.stop_evaluator(evaluator)
            await evaluator_api.stop_all_evaluator_channels(self.matrix_id)
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

    async def _init_evaluators(self):
        self.matrix_id = await evaluator_api.initialize_evaluators(self.backtesting_config, self.tentacles_setup_config)
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
            self.evaluators = await evaluator_api.create_all_type_evaluators(
                self.tentacles_setup_config,
                matrix_id=self.matrix_id,
                exchange_name=exchange_configuration.exchange_name,
                bot_id=self.bot_id,
                symbols_by_crypto_currencies=exchange_configuration.symbols_by_crypto_currencies,
                symbols=exchange_configuration.symbols,
                time_frames=exchange_configuration.time_frames_without_real_time,
                real_time_time_frames=exchange_configuration.real_time_time_frames)

    async def _create_service_feeds(self):
        for feed in self.service_feeds:
            if not await service_api.start_service_feed(feed, False, {}):
                self.logger.error(f"Failed to start {feed.get_name()}. Evaluators requiring this service feed "
                                  f"might not work properly")

    async def _init_exchanges(self):
        self.backtesting = await backtesting_api.initialize_backtesting(self.backtesting_config,
                                                                        exchange_ids=self.exchange_manager_ids,
                                                                        matrix_id=self.matrix_id,
                                                                        data_files=self.backtesting_files)
        # modify_backtesting_channels before creating exchanges as they require the current backtesting time to
        # initialize
        await backtesting_api.adapt_backtesting_channels(self.backtesting,
                                                         self.backtesting_config,
                                                         importers.ExchangeDataImporter,
                                                         run_on_common_part_only=self.run_on_common_part_only)

        for exchange_class_string in self.symbols_to_create_exchange_classes.keys():
            exchange_builder = trading_api.create_exchange_builder(self.backtesting_config, exchange_class_string) \
                .has_matrix(self.matrix_id) \
                .use_tentacles_setup_config(self.tentacles_setup_config) \
                .set_bot_id(self.bot_id) \
                .is_simulated() \
                .is_rest_only() \
                .is_backtesting(self.backtesting)
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
        error += f"{sys.getrefcount(actual[1][i])} references on {actual[1][i]}"
        return error
