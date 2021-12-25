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
import multiprocessing
import os
import itertools
import enum
import random
import copy
import asyncio
import concurrent.futures
import time
import numpy
import logging
import ctypes

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging
import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_commons.databases as databases
import octobot_trading.modes.scripting_library as scripting_library # TODO remove
import octobot.api.backtesting as octobot_backtesting_api
import octobot_backtesting.errors as backtesting_errors
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants


class ConfigTypes(enum.Enum):
    NUMBER = "number"
    BOOLEAN = "boolean"
    OPTIONS = "options"
    UNKNOWN = "unknown"


class NoMoreRunError(Exception):
    pass


class StrategyDesignOptimizer:
    MAX_OPTIMIZER_RUNS = 100000
    SHARED_KEEP_RUNNING_KEY = "keep_running"

    RUN_SCHEDULE_TABLE = "schedule"
    CONFIG_KEY = "key"
    CONFIG_USER_INPUT = "user_input"
    CONFIG_VALUE = "value"
    CONFIG_TENTACLE = "tentacle"
    CONFIG_TYPE = "type"
    CONFIG_ENABLED = "enabled"
    CONFIG_MIN = "min"
    CONFIG_MAX = "max"
    CONFIG_STEP = "step"
    CONFIG_RUNS = "runs"
    CONFIG_DATA_FILES = "data_files"
    CONFIG_ID = "id"
    CONFIG_DELETED = "deleted"

    def __init__(self, trading_mode, config, tentacles_setup_config, optimizer_config, data_files):
        self.config = config
        self.base_tentacles_setup_config = tentacles_setup_config
        self.trading_mode = trading_mode
        self.optimizer_config = optimizer_config
        self.data_files = data_files
        self.optimizer_id = None
        self.current_backtesting_id = None
        self.runs_schedule = None
        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.database_manager = databases.DatabaseManager(self.trading_mode)

        self.is_computing = False
        self.current_run_id = 0
        self.total_nb_runs = 0
        self.keep_running = True
        self.process_pool_handle = None

    async def initialize(self, is_resuming):
        if not is_resuming:
            taken_ids = await self.get_queued_optimizer_ids()
            self.optimizer_id = await self.database_manager.generate_new_optimizer_id(taken_ids)
            self.database_manager.optimizer_id = self.optimizer_id
            await self.database_manager.initialize()
            await self._store_backtesting_runs_schedule()

    def get_name(self) -> str:
        return f"{self.trading_mode.get_name()}_{self.__class__.__name__}"

    async def multi_processed_optimize(self, optimizer_ids=None, randomly_chose_runs=False):
        optimizer_ids = optimizer_ids or [self.optimizer_id]
        self.is_computing = True
        global_t0 = time.time()
        lock = multiprocessing.RLock()
        shared_keep_running = multiprocessing.Value(ctypes.c_bool, True)
        try:
            self.current_run_id = 1
            with multiprocessing_util.registered_lock_and_shared_elements(
                    commons_enums.MultiprocessingLocks.DBLock.value, lock,
                    {self.SHARED_KEEP_RUNNING_KEY: shared_keep_running}),\
                 concurrent.futures.ProcessPoolExecutor(
                    initializer=multiprocessing_util.register_lock_and_shared_elements,
                    initargs=(commons_enums.MultiprocessingLocks.DBLock.value,
                              lock, {self.SHARED_KEEP_RUNNING_KEY: shared_keep_running})) as pool:
                self.logger.info(f"Dispatching optimizer backtesting runs into {pool._max_workers} parallel processes "
                                 f"(based on the current computer physical processors).")
                coros = []
                for _ in range(pool._max_workers):
                    coros.append(
                            asyncio.get_event_loop().run_in_executor(
                                pool,
                                self.find_optimal_configuration_wrapper,
                                optimizer_ids,
                                randomly_chose_runs
                            )
                        )
                self.process_pool_handle = await asyncio.gather(*coros)
        except Exception as e:
            self.logger.exception(e, True, f"Error when running optimizer processes: {e}")
        finally:
            self.process_pool_handle = None
            self.is_computing = False
        self.logger.info(f"Optimizer runs complete in {time.time() - global_t0} seconds.")

    def _init_optimizer_process_logger(self):
        # init basic logger
        logging.basicConfig(
            format=f'[{self.__class__.__name__} %(process)d] %(levelname)-6s %(name)-20s '
                   f'%(filename)-s:%(lineno)-8s %(message)s',
            level=logging.ERROR
        )

    def find_optimal_configuration_wrapper(self, optimizer_ids, randomly_chose_runs=False):
        self._init_optimizer_process_logger()
        asyncio.run(self.find_optimal_configuration(optimizer_ids, randomly_chose_runs=randomly_chose_runs))

    async def find_optimal_configuration(self, optimizer_ids, randomly_chose_runs=False):
        # need to load tentacles when in new process
        tentacles_manager_api.reload_tentacle_info()
        try:
            for optimizer_id in optimizer_ids:
                if optimizer_id is None:
                    # should not happen but in case it does, drop the run
                    await self.drop_optimizer_run_from_queue(optimizer_id)
                    continue
                try:
                    while self._should_keep_running():
                        await self.run_single_iteration(optimizer_id, randomly_chose_runs=randomly_chose_runs)
                except NoMoreRunError:
                    await self.drop_optimizer_run_from_queue(optimizer_id)
        except concurrent.futures.CancelledError:
            self.logger.info("Cancelled run")
            raise

    async def drop_optimizer_run_from_queue(self, optimizer_id):
        async with databases.DBWriter.database(
                self.database_manager.get_optimizer_runs_schedule_identifier(), with_lock=True) as writer:
            query = await writer.search()
            await writer.delete(self.RUN_SCHEDULE_TABLE, query.id == optimizer_id)

    def _should_keep_running(self):
        try:
            return multiprocessing_util.get_shared_element(self.SHARED_KEEP_RUNNING_KEY).value
        except KeyError:
            return self.keep_running

    def cancel(self):
        self.keep_running = False
        try:
            multiprocessing_util.get_shared_element(self.SHARED_KEEP_RUNNING_KEY).value = False
        except KeyError:
            pass
        if self.process_pool_handle is not None:
            self.process_pool_handle.cancel()

    async def _get_remaining_runs_count_from_db(self, optimizer_id):
        async with databases.DBReader.database(self.database_manager.get_optimizer_runs_schedule_identifier(),
                                               with_lock=True) as reader:
            run_data = await self._get_run_data_from_db(optimizer_id, reader)
        if run_data and run_data[0][self.CONFIG_RUNS]:
            return len(run_data[0][self.CONFIG_RUNS])
        return 0

    async def get_overall_progress(self):
        if self.optimizer_id is None:
            remaining_runs = len(await self.get_run_queue(self.trading_mode))
        else:
            remaining_runs = await self._get_remaining_runs_count_from_db(self.optimizer_id)
        if self.is_computing and remaining_runs == 0:
            remaining_runs = 1
        done_runs = self.total_nb_runs - remaining_runs
        return int(done_runs / self.total_nb_runs * 100) if self.total_nb_runs else 0

    async def is_in_progress(self):
        return self.is_computing

    def get_current_test_suite_progress(self):
        return 0

    def get_errors_description(self):
        return ""

    async def _get_run_data_from_db(self, optimizer_id, reader):
        if optimizer_id is None:
            raise RuntimeError("No optimizer id")
        query = await reader.search()
        return await reader.select(self.RUN_SCHEDULE_TABLE, query.id == optimizer_id)

    async def get_queued_optimizer_ids(self):
        return [
            run.get(self.CONFIG_ID, None)
            for run in (await self.get_run_queue(self.trading_mode))
        ]

    async def resume(self, optimizer_ids, randomly_chose_runs):
        self.total_nb_runs = len(optimizer_ids)
        await self.multi_processed_optimize(optimizer_ids=optimizer_ids, randomly_chose_runs=randomly_chose_runs)

    @classmethod
    async def get_run_queue(cls, trading_mode):
        db_manager = databases.DatabaseManager(trading_mode)
        try:
            async with databases.DBReader.database(db_manager.get_optimizer_runs_schedule_identifier(),
                                                   with_lock=True) as reader:
                return await reader.all(cls.RUN_SCHEDULE_TABLE)
        except commons_errors.DatabaseNotFoundError:
            return []

    @classmethod
    def _contains_run(cls, optimizer_run, run_data):
        for run in optimizer_run.get(cls.CONFIG_RUNS).values():
            if len(run) != len(run_data):
                return False
            all_equal = True
            for reference_run_input_details in run:
                found_input_detail = False
                for run_input_details in run_data:
                    try:
                        if all(run_input_details[key] == val for key, val in reference_run_input_details.items()):
                            found_input_detail = True
                            break
                    except KeyError:
                        pass
                if not found_input_detail:
                    all_equal = False
                    break
            if all_equal:
                return True
        return False

    @classmethod
    async def update_run_queue(cls, trading_mode, updated_queue):
        db_manager = databases.DatabaseManager(trading_mode)
        async with databases.DBWriterReader.database(db_manager.get_optimizer_runs_schedule_identifier(),
                                                     with_lock=True) as writer_reader:
            query = await writer_reader.search()
            try:
                db_optimizer_run = \
                    (await writer_reader.select(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue[cls.CONFIG_ID]))[0]
                runs = updated_queue[cls.CONFIG_RUNS]
                # remove deleted runs and runs that are not in the queue anymore (already running or done)
                for run_data in copy.copy(runs):
                    if cls._contains_run(db_optimizer_run, run_data):
                        for run_input in run_data:
                            if run_input.get(cls.CONFIG_DELETED, False):
                                runs.remove(run_data)
                                break
                            run_input.pop(cls.CONFIG_DELETED)
                    else:
                        runs.remove(run_data)
                # ensure runs are a dict
                updated_queue[cls.CONFIG_RUNS] = {
                    index: run
                    for index, run in enumerate(runs)
                }
                # replace queue by updated one to keep order
                query = await writer_reader.search()
                if runs:
                    await writer_reader.update(cls.RUN_SCHEDULE_TABLE, updated_queue, query.id == updated_queue["id"])
                else:
                    await writer_reader.delete(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue["id"])
            except IndexError:
                # optimizer run not in db anymore
                pass
            return updated_queue

    async def run_single_iteration(self, optimizer_id, randomly_chose_runs=False):
        data_files = run_data = run_id = run_details = None
        async with databases.DBWriterReader.database(
                self.database_manager.get_optimizer_runs_schedule_identifier(), with_lock=True) \
                as writer_reader:
            run_data = await self._get_run_data_from_db(optimizer_id, writer_reader)
            if run_data and run_data[0][self.CONFIG_RUNS]:
                runs = run_data[0][self.CONFIG_RUNS]
                data_files = run_data[0][self.CONFIG_DATA_FILES]
                run_ids = list(runs)
                run_count = len(run_ids)
                run_id = random.randrange(run_count) if randomly_chose_runs else run_ids[0]
                run_details = runs.pop(run_id)
            if data_files:
                query = await writer_reader.search()
                updated_data = {
                    self.CONFIG_RUNS: run_data[0][self.CONFIG_RUNS]
                }
                await writer_reader.update(self.RUN_SCHEDULE_TABLE, updated_data, query.id == optimizer_id)

        if data_files and run_details:
            # start backtesting run ids at 1
            backtesting_run_id = int(run_id) + 1
            return await self._run_with_config(optimizer_id, data_files, backtesting_run_id, run_details)
        raise NoMoreRunError("Nothing to run")

    async def _run_with_config(self, optimizer_id, data_files, run_id, run_config):
        self.logger.debug(f"Running optimizer with id {optimizer_id} "
                          f"on backtesting {run_id} with config {run_config}")
        self._update_config_for_optimizer(optimizer_id, run_id)
        tentacles_setup_config = self._get_custom_tentacles_setup_config(optimizer_id, run_id, run_config)
        independent_backtesting = None
        try:
            # reset possible remaining caches
            await databases.CacheManager().reset()
            config_to_use = copy.deepcopy(self.config)
            independent_backtesting = octobot_backtesting_api.create_independent_backtesting(
                config_to_use,
                tentacles_setup_config,
                data_files,
            )
            await octobot_backtesting_api.initialize_and_run_independent_backtesting(independent_backtesting,
                                                                                     log_errors=False)
            await octobot_backtesting_api.join_independent_backtesting(independent_backtesting)
            return independent_backtesting
        except backtesting_errors.MissingTimeFrame:
            # ignore this exception: is due to missing of the only required time frame
            return independent_backtesting
        except Exception as e:
            self.logger.exception(e, True, str(e))
            return independent_backtesting
        finally:
            if independent_backtesting is not None:
                await independent_backtesting.stop()

    def _update_config_for_optimizer(self, optimizer_id, run_id):
        self.config[commons_constants.CONFIG_OPTIMIZER_ID] = optimizer_id
        self.config[commons_constants.CONFIG_BACKTESTING_ID] = run_id

    def _get_custom_tentacles_setup_config(self, optimizer_id, run_id, run_config):
        local_tentacles_setup_config = copy.deepcopy(self.base_tentacles_setup_config)
        run_db_manager = databases.DatabaseManager(self.trading_mode,
                                                   optimizer_id=optimizer_id, backtesting_id=run_id)
        run_folder = run_db_manager.get_backtesting_run_folder()
        tentacles_setup_config_path = os.path.join(run_folder, commons_constants.CONFIG_TENTACLES_FILE)
        tentacles_manager_api.set_tentacles_setup_configuration_path(local_tentacles_setup_config,
                                                                     tentacles_setup_config_path)
        # save updated config for each custom parameter tentacle
        # and import config of remaining tentacles: add missing tentacles into tentacles_updates with nothing to update
        tentacles_updates = {
            tentacle: {}
            for tentacle in tentacles_manager_api.get_activated_tentacles(self.base_tentacles_setup_config)
            if tentacles_manager_api.has_profile_local_configuration(self.base_tentacles_setup_config, tentacle)
        }
        for input_config in run_config:
            if input_config[self.CONFIG_TENTACLE] not in tentacles_updates:
                tentacles_updates[input_config[self.CONFIG_TENTACLE]] = {}
            tentacles_updates[input_config[self.CONFIG_TENTACLE]][input_config[self.CONFIG_USER_INPUT]] = \
                input_config[self.CONFIG_VALUE]
        self._ensure_local_config_folders(run_folder)
        for tentacle, updated_values in tentacles_updates.items():
            tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle)
            current_config = tentacles_manager_api.get_tentacle_config(self.base_tentacles_setup_config,
                                                                       tentacle_class)
            current_config.update(updated_values)
            tentacles_manager_api.update_tentacle_config(local_tentacles_setup_config, tentacle_class, current_config)
        return local_tentacles_setup_config

    @staticmethod
    def _ensure_local_config_folders(run_folder):
        if not os.path.exists(run_folder):
            os.makedirs(run_folder)
        tentacles_specific_config_folder = os.path.join(run_folder,
                                                        tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER)
        if not os.path.exists(tentacles_specific_config_folder):
            os.mkdir(tentacles_specific_config_folder)

    async def _store_backtesting_runs_schedule(self):
        runs = self._generate_runs()
        await self._save_run_schedule(runs)
        return runs

    def _generate_runs(self):
        iterations = [i for i in self._get_config_possible_iterations() if i]
        if iterations:
            return {index: run for index, run in enumerate(itertools.product(*iterations))}
        raise RuntimeError("No optimizer run to schedule with this configuration")

    def _get_config_possible_iterations(self):
        return [
            self._generate_possible_values(config_element)
            for config_element in self._get_config_elements()
        ]

    def _generate_possible_values(self, config_element):
        if not config_element:
            return {}
        values = []
        try:
            if config_element[self.CONFIG_ENABLED]:
                if config_element[self.CONFIG_TYPE] in (ConfigTypes.OPTIONS, ConfigTypes.BOOLEAN):
                    values = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
                if config_element[self.CONFIG_TYPE] is ConfigTypes.NUMBER:
                    config = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
                    values = [v.item()
                              for v in numpy.arange(config[self.CONFIG_MIN],
                                                    config[self.CONFIG_MAX],
                                                    config[self.CONFIG_STEP])]
            return [
                {
                    self.CONFIG_USER_INPUT: config_element[self.CONFIG_USER_INPUT],
                    self.CONFIG_TENTACLE: config_element[self.CONFIG_VALUE][self.CONFIG_TENTACLE],
                    self.CONFIG_VALUE: value
                }
                for value in values
            ]
        except ZeroDivisionError as e:
            raise ZeroDivisionError("Step value has to be greater than 0") from e

    def _get_config_elements(self):
        for key, val in self.optimizer_config.items():
            yield {
                self.CONFIG_KEY: key,
                self.CONFIG_ENABLED: val[self.CONFIG_ENABLED],
                self.CONFIG_USER_INPUT: val[self.CONFIG_USER_INPUT],
                self.CONFIG_VALUE: val,
                self.CONFIG_TYPE: self._get_config_type(val)
            }

    def _get_config_type(self, value):
        config_values = value[self.CONFIG_VALUE]
        if isinstance(config_values, list):
            if not config_values:
                return ConfigTypes.OPTIONS
            if isinstance(config_values[0], bool):
                return ConfigTypes.BOOLEAN
            else:
                return ConfigTypes.OPTIONS
        if isinstance(config_values, dict):
            try:
                if all(isinstance(config_values[key], (float, int))
                       for key in [self.CONFIG_MIN, self.CONFIG_MAX, self.CONFIG_STEP]):
                    return ConfigTypes.NUMBER
            except KeyError:
                pass
        return ConfigTypes.UNKNOWN

    async def _save_run_schedule(self, runs):
        self.runs_schedule = {
            self.CONFIG_RUNS: runs,
            self.CONFIG_DATA_FILES: self.data_files,
            self.CONFIG_ID: self.optimizer_id
        }
        self.total_nb_runs = len(runs)
        async with databases.DBWriter.database(self.database_manager.get_optimizer_runs_schedule_identifier(),
                                               with_lock=True) as writer:
            await writer.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
