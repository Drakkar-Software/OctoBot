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
import decimal
import hashlib
import json
import multiprocessing
import os
import itertools
import enum
import queue
import copy
import asyncio
import concurrent.futures
import time
import numpy
import logging
import ctypes
import random

import octobot_commons.optimization_campaign as optimization_campaign
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging
import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_commons.databases as databases
import octobot_commons.dict_util as dict_util
import octobot_commons.logical_operators as logical_operators
import octobot_backtesting.errors as backtesting_errors
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_services.api as services_api
import octobot_services.enums as services_enums


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
    SHARED_RUN_TIMES_KEY = "run_times"
    SHARED_RUNS_QUEUES_KEY = "runs_queues"
    START_QUEUE_KEY = "start_queue"
    DONE_QUEUE_KEY = "done_queue"
    DB_UPDATE_PERIOD = 15   # update run database at the end of each period

    RUN_SCHEDULE_TABLE = "schedule"
    CONFIG_KEY = "key"
    CONFIG_USER_INPUT = "user_input"
    CONFIG_USER_INPUTS = "user_inputs"
    CONFIG_FILTER_SETTINGS = "filters_settings"
    CONFIG_VALUE = "value"
    CONFIG_TENTACLE = "tentacle"
    CONFIG_NESTED_TENTACLE_SEPARATOR = "_------_"
    CONFIG_TYPE = "type"
    CONFIG_ENABLED = "enabled"
    CONFIG_MIN = "min"
    CONFIG_MAX = "max"
    CONFIG_STEP = "step"
    CONFIG_RUNS = "runs"
    CONFIG_ID = "id"
    CONFIG_DELETED = "deleted"
    CONFIG_DELETE_EVERY_RUN = "delete_every_run"
    CONFIG_ROLE = "role"

    def __init__(self, trading_mode, config, tentacles_setup_config, optimizer_config,
                 optimizer_id=None, queue_size=None):
        self.config = config
        self.base_tentacles_setup_config = tentacles_setup_config
        self.trading_mode = trading_mode
        self.optimizer_config = optimizer_config
        self.optimizer_id = optimizer_id
        self.queue_size = queue_size
        self.current_backtesting_id = None
        self.runs_schedule = None
        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.optimization_campaign_name = optimization_campaign.OptimizationCampaign.get_campaign_name(
            tentacles_setup_config
        )
        self.run_dbs_identifier = databases.RunDatabasesIdentifier(self.trading_mode, self.optimization_campaign_name)

        self.is_computing = False
        self.is_finished = False
        self.total_nb_runs = 0
        self.prioritized_optimizer_ids = []
        self.empty_the_queue = False
        self.active_processes_count = 0
        self.keep_running = True
        self.process_pool_handle = None
        self.average_run_time = 0
        self.first_iteration_time = 0

    async def initialize(self, is_resuming):
        if not is_resuming:
            await self.generate_and_save_run()

    def get_name(self):
        return f"{self.trading_mode.get_name()}_{self.__class__.__name__}"

    async def _create_run_queues(self, optimizer_id):
        run_data, run_data_by_hash = await self._get_optimizer_runs_details_and_hashes(optimizer_id)
        start_queue = multiprocessing.Queue(len(run_data_by_hash))
        done_queue = multiprocessing.Queue(len(run_data_by_hash))
        for run_hash in run_data_by_hash:
            start_queue.put(run_hash)
        return {
            self.START_QUEUE_KEY: start_queue,
            self.DONE_QUEUE_KEY: done_queue
        }

    async def multi_processed_optimize(self,
                                       data_files,
                                       optimizer_ids=None,
                                       randomly_chose_runs=False,
                                       start_timestamp=None,
                                       end_timestamp=None,
                                       empty_the_queue=False,
                                       required_idle_cores=0,
                                       notify_when_complete=False):
        optimizer_ids = optimizer_ids or [self.optimizer_id]
        self.is_computing = True
        self.is_finished = False
        self.average_run_time = 0
        self.active_processes_count = multiprocessing.cpu_count() - abs(required_idle_cores)
        self.total_nb_runs = await self._get_total_nb_runs(optimizer_ids)
        global_t0 = time.time()
        lock = multiprocessing.RLock()
        shared_keep_running = multiprocessing.Value(ctypes.c_bool, True)
        shared_run_time = multiprocessing.Array(ctypes.c_float, [0.0 for _ in range(self.active_processes_count)])
        try:
            async for selected_optimizer_ids in self._all_optimizer_ids(optimizer_ids, empty_the_queue):
                run_queues_by_optimizer_id = {
                    optimizer_id: await self._create_run_queues(optimizer_id)
                    for optimizer_id in selected_optimizer_ids
                }
                try:
                    await self._run_multi_processed_optimizer(
                        lock, required_idle_cores,
                        shared_keep_running, shared_run_time, run_queues_by_optimizer_id,
                        data_files, start_timestamp, end_timestamp)
                finally:
                    # properly empty and close queues to avoid underlying thread issues
                    for optimizer_id, run_queues in run_queues_by_optimizer_id.items():
                        try:
                            await self._update_runs_from_done_queue(run_queues, optimizer_id)
                        except Exception as e:
                            self.logger.exception(e, True, f"Error on final db queue update: {e}")
                        for run_queue in run_queues.values():
                            # empty queues
                            while not run_queue.empty():
                                run_queue.get()
                            run_queue.close()
                            run_queue.cancel_join_thread()
        except Exception as e:
            self.logger.exception(e, True, f"Error when running optimizer processes: {e}")
        finally:
            if notify_when_complete:
                await services_api.send_notification(
                    services_api.create_notification(f"Your strategy optimizer just finished.",
                                                     sound=services_enums.NotificationSound.FINISHED_PROCESSING,
                                                     category=services_enums.NotificationCategory.OTHER)
                )
            self.process_pool_handle = None
            self.is_computing = False
            self.is_finished = True
        self.logger.info(f"Optimizer runs complete in {time.time() - global_t0} seconds.")

    async def _run_multi_processed_optimizer(self, lock, required_idle_cores,
                                             shared_keep_running, shared_run_time, run_queues_by_optimizer_id,
                                             data_files, start_timestamp, end_timestamp):
        with multiprocessing_util.registered_lock_and_shared_elements(
                commons_enums.MultiprocessingLocks.DBLock.value,
                lock,
                {
                    self.SHARED_KEEP_RUNNING_KEY: shared_keep_running,
                    self.SHARED_RUN_TIMES_KEY: shared_run_time,
                    self.SHARED_RUNS_QUEUES_KEY: run_queues_by_optimizer_id,
                }), \
                concurrent.futures.ProcessPoolExecutor(
                    max_workers=self.active_processes_count,
                    initializer=multiprocessing_util.register_lock_and_shared_elements,
                    initargs=(commons_enums.MultiprocessingLocks.DBLock.value,
                              lock,
                              {
                                  self.SHARED_KEEP_RUNNING_KEY: shared_keep_running,
                                  self.SHARED_RUN_TIMES_KEY: shared_run_time,
                                  self.SHARED_RUNS_QUEUES_KEY: run_queues_by_optimizer_id,
                              })) as pool:
            coros = []
            self.logger.info(f"Dispatching optimizer backtesting runs into {self.active_processes_count} "
                             f"parallel processes (based on the current computer physical processors).")
            if self.active_processes_count < 1:
                idle_cores_message = f"Requiring to leave {required_idle_cores} idle core. " \
                    if required_idle_cores else ""
                raise RuntimeError(f"{idle_cores_message}At lease one core is required to "
                                   f"start a strategy optimizer. "
                                   f"There are {multiprocessing.cpu_count()} total available cores on this computer.")
            for index in range(self.active_processes_count):
                coros.append(
                    asyncio.get_event_loop().run_in_executor(
                        pool,
                        self.find_optimal_configuration_wrapper,
                        data_files,
                        index == 0,
                        start_timestamp,
                        end_timestamp
                    )
                )
            self.process_pool_handle = await asyncio.gather(*coros)

    async def _all_optimizer_ids(self, prioritized_ids, empty_the_queue):
        if prioritized_ids:
            yield prioritized_ids
        if empty_the_queue:
            updated_ids = await self.get_queued_optimizer_ids()
            while self._should_keep_running() and updated_ids:
                # reselect from database in case new runs were added
                yield updated_ids
                updated_ids = await self.get_queued_optimizer_ids()

    def _init_optimizer_process_logger(self):
        # init basic logger
        logging.basicConfig(
            format=f'[{self.__class__.__name__} %(process)d] %(levelname)-6s %(name)-20s '
                   f'%(filename)-s:%(lineno)-8s %(message)s',
            level=logging.ERROR
        )

    def find_optimal_configuration_wrapper(self,
                                           data_files,
                                           update_database=False,
                                           start_timestamp=None,
                                           end_timestamp=None):
        self._init_optimizer_process_logger()
        run_queues_by_optimizer_id = multiprocessing_util.get_shared_element(self.SHARED_RUNS_QUEUES_KEY)
        asyncio.run(self.find_optimal_configuration(run_queues_by_optimizer_id,
                                                    data_files,
                                                    update_database=update_database,
                                                    start_timestamp=start_timestamp,
                                                    end_timestamp=end_timestamp))

    async def find_optimal_configuration(self,
                                         run_queues_by_optimizer_id,
                                         data_files,
                                         update_database=False,
                                         start_timestamp=None,
                                         end_timestamp=None):
        # need to load tentacles when in new process
        tentacles_manager_api.reload_tentacle_info()
        run_queues = optimizer_id = None
        try:
            for optimizer_id, run_queues in run_queues_by_optimizer_id.items():
                await self._execute_optimizer_run(optimizer_id, run_queues, update_database, data_files,
                                                  start_timestamp, end_timestamp)

        except concurrent.futures.CancelledError:
            self.logger.info("Cancelled run")
            if update_database and run_queues is not None and optimizer_id is not None:
                # stopped run: update queue
                await self._update_runs_from_done_queue(run_queues, optimizer_id)
            raise
        # let done queue push thread finish
        # time.sleep(0.1)

    async def _get_optimizer_runs_details_and_hashes(self, optimizer_id):
        async with databases.DBReader.database(self.run_dbs_identifier.get_optimizer_runs_schedule_identifier()) \
                as reader:
            run_data = await self._get_run_data_from_db(optimizer_id, reader)
        if run_data:
            return run_data, {
                self.get_run_hash(run_details): run_details
                for run_details in run_data[0][self.CONFIG_RUNS].values()
            }
        raise NoMoreRunError

    async def _execute_optimizer_run(self, optimizer_id, run_queues, update_database, data_files,
                                     start_timestamp, end_timestamp):
        if update_database and optimizer_id is None:
            # should not happen but in case it does, drop the run
            await self.drop_optimizer_run_from_queue(optimizer_id)
            return
        try:
            run_data, run_data_by_hash = await self._get_optimizer_runs_details_and_hashes(optimizer_id)
            t_start = time.time()
            last_db_update_time = t_start
            while self._should_keep_running():
                await self.run_single_iteration(optimizer_id,
                                                run_queues,
                                                run_data_by_hash,
                                                run_data,
                                                data_files,
                                                start_timestamp=start_timestamp,
                                                end_timestamp=end_timestamp)
                if self.first_iteration_time == 0:
                    self.first_iteration_time = time.time() - t_start
                    self._register_run_time(self.first_iteration_time)
                if update_database and time.time() - last_db_update_time > self.DB_UPDATE_PERIOD:
                    await self._update_runs_from_done_queue(run_queues, optimizer_id)
                    last_db_update_time = time.time()
            if update_database:
                # stopped run: update queue
                await self._update_runs_from_done_queue(run_queues, optimizer_id)
        except NoMoreRunError:
            await self.drop_optimizer_run_from_queue(optimizer_id)
        except Exception as e:
            self.logger.exception(e, True, f"Error while running iteration: {e}")

    async def _update_runs_from_done_queue(self, run_queues, optimizer_id):
        completed_run_hashes = set()
        while not run_queues[self.DONE_QUEUE_KEY].empty():
            completed_run_hashes.add(run_queues[self.DONE_QUEUE_KEY].get(timeout=0.1))
        if not completed_run_hashes:
            return
        async with databases.DBWriterReader.database(
                self.run_dbs_identifier.get_optimizer_runs_schedule_identifier(), with_lock=True) \
                as writer_reader:
            run_data = await self._get_run_data_from_db(optimizer_id, writer_reader)
            if not run_data:
                # db already empty, nothing to do
                return
            updated_queue = run_data[0]
            runs = [run_details
                    for run_details in updated_queue[self.CONFIG_RUNS].values()
                    if self.get_run_hash(run_details) not in completed_run_hashes]
            updated_queue[self.CONFIG_RUNS] = {
                index: run
                for index, run in enumerate(runs)
            }
            query = await writer_reader.search()
            if runs and runs[0]:
                await writer_reader.update(self.RUN_SCHEDULE_TABLE, updated_queue,
                                           query.id == updated_queue["id"])

    async def drop_optimizer_run_from_queue(self, optimizer_id):
        async with databases.DBWriter.database(
                self.run_dbs_identifier.get_optimizer_runs_schedule_identifier(), with_lock=True) as writer:
            query = await writer.search()
            await writer.delete(self.RUN_SCHEDULE_TABLE, query.id == optimizer_id)

    def _should_keep_running(self):
        try:
            return multiprocessing_util.get_shared_element(self.SHARED_KEEP_RUNNING_KEY).value
        except KeyError:
            return self.keep_running

    def _register_run_time(self, run_time):
        try:
            shared_run_times = multiprocessing_util.get_shared_element(self.SHARED_RUN_TIMES_KEY)
            with shared_run_times:
                for index, value in enumerate(shared_run_times):
                    if value == 0.0:
                        shared_run_times[index] = run_time
                        return
        except KeyError:
            pass

    def get_average_run_time(self):
        if self.average_run_time == 0:
            try:
                run_times = [v for v in multiprocessing_util.get_shared_element(self.SHARED_RUN_TIMES_KEY)]
            except KeyError:
                run_times = []
            set_run_times = [run_time for run_time in run_times if run_time > 0]
            if not set_run_times:
                return 0
            average_run_time = numpy.average(set_run_times)
            if len(set_run_times) >= self.active_processes_count:
                self.average_run_time = average_run_time
            return average_run_time
        return self.average_run_time

    def cancel(self):
        self.keep_running = False
        try:
            multiprocessing_util.get_shared_element(self.SHARED_KEEP_RUNNING_KEY).value = False
        except KeyError:
            pass
        if self.process_pool_handle is not None:
            self.process_pool_handle.cancel()

    async def _get_remaining_runs_count_from_multi_process_queue(self, optimizer_ids):
        try:
            if not isinstance(optimizer_ids, list):
                optimizer_ids = [optimizer_ids]
            run_queues_by_optimizer_id = multiprocessing_util.get_shared_element(self.SHARED_RUNS_QUEUES_KEY)
            return sum(run_queues[self.START_QUEUE_KEY].qsize()
                       for optimizer_id, run_queues in run_queues_by_optimizer_id.items()
                       if optimizer_id in optimizer_ids or self.empty_the_queue)
        except KeyError:
            return 0

    async def get_overall_progress(self):
        if self.optimizer_id is None:
            remaining_runs = await self._get_remaining_runs_count_from_multi_process_queue(
                self.prioritized_optimizer_ids)
        else:
            remaining_runs = await self._get_remaining_runs_count_from_multi_process_queue(
                self.optimizer_id)
        if self.is_computing and remaining_runs == 0:
            remaining_runs = 1
        done_runs = self.total_nb_runs - remaining_runs
        remaining_time = remaining_runs * self.get_average_run_time() / self.active_processes_count \
            if self.active_processes_count else 0
        return int(done_runs / self.total_nb_runs * 100) if self.total_nb_runs else 0, remaining_time

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
            for run in (await self.get_run_queue(self.trading_mode, self.optimization_campaign_name))
        ]

    async def resume(self, data_files, optimizer_ids, randomly_chose_runs,
                     start_timestamp=None,
                     end_timestamp=None,
                     empty_the_queue=False,
                     required_idle_cores=0,
                     notify_when_complete=False):
        self.empty_the_queue = empty_the_queue
        self.total_nb_runs = await self._get_total_nb_runs(optimizer_ids)
        self.prioritized_optimizer_ids = optimizer_ids
        await self.multi_processed_optimize(data_files,
                                            optimizer_ids=optimizer_ids,
                                            randomly_chose_runs=randomly_chose_runs,
                                            start_timestamp=start_timestamp,
                                            end_timestamp=end_timestamp,
                                            empty_the_queue=empty_the_queue,
                                            required_idle_cores=required_idle_cores,
                                            notify_when_complete=notify_when_complete)

    async def _get_total_nb_runs(self, optimizer_ids):
        full_queue = await self.get_run_queue(self.trading_mode)
        if self.empty_the_queue:
            return sum(len(run[self.CONFIG_RUNS]) for run in full_queue)
        return sum(len(run[self.CONFIG_RUNS]) for run in full_queue if run[self.CONFIG_ID] in optimizer_ids)

    async def generate_and_save_run(self):
        taken_ids = await self.get_queued_optimizer_ids()
        self.optimizer_id = await self.run_dbs_identifier.generate_new_optimizer_id(taken_ids) \
            if self.optimizer_id is None else self.optimizer_id
        self.run_dbs_identifier.optimizer_id = self.optimizer_id
        await self.run_dbs_identifier.initialize()
        return await self._generate_and_store_backtesting_runs_schedule()

    @classmethod
    async def get_run_queue(cls, trading_mode, campaign_name=None):
        campaign_name = campaign_name or optimization_campaign.OptimizationCampaign.get_campaign_name()
        run_dbs_identifier = databases.RunDatabasesIdentifier(trading_mode, campaign_name)
        try:
            async with databases.DBReader.database(run_dbs_identifier.get_optimizer_runs_schedule_identifier(),
                                                   with_lock=True) as reader:
                return await reader.all(cls.RUN_SCHEDULE_TABLE)
        except commons_errors.DatabaseNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    @classmethod
    def get_run_hash(cls, run_data):
        return hashlib.sha256(json.dumps([
            {
                cls.CONFIG_USER_INPUT: run_data_item[cls.CONFIG_USER_INPUT],
                cls.CONFIG_TENTACLE: run_data_item[cls.CONFIG_TENTACLE],
                cls.CONFIG_VALUE: float(run_data_item[cls.CONFIG_VALUE])
                if isinstance(run_data_item[cls.CONFIG_VALUE], int) else run_data_item[cls.CONFIG_VALUE]
            }
            for run_data_item in run_data
        ]).encode()).hexdigest()

    @classmethod
    async def update_run_queue(cls, trading_mode, updated_queue):
        run_dbs_identifier = databases.RunDatabasesIdentifier(
            trading_mode, optimization_campaign.OptimizationCampaign.get_campaign_name())
        async with databases.DBWriterReader.database(run_dbs_identifier.get_optimizer_runs_schedule_identifier(),
                                                     with_lock=True) as writer_reader:
            query = await writer_reader.search()
            try:
                runs = updated_queue[cls.CONFIG_RUNS]
                if updated_queue[cls.CONFIG_DELETE_EVERY_RUN]:
                    # delete every run, just delete the whole optimizer run
                    await writer_reader.delete(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue["id"])
                    return updated_queue
                db_optimizer_run = []
                try:
                    db_optimizer_run = \
                        (await writer_reader.select(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue[cls.CONFIG_ID]))[0]
                except json.JSONDecodeError:
                    pass
                existing_runs = set(
                    cls.get_run_hash(run_data)
                    for run_data in db_optimizer_run.get(cls.CONFIG_RUNS).values()
                )
                to_remove_indexes = []
                # remove deleted runs and runs that are not in the queue anymore (already running or done)
                for run_index, run_data in enumerate(copy.copy(runs)):
                    if cls.get_run_hash(run_data) in existing_runs:
                        for run_input in run_data:
                            if run_input.get(cls.CONFIG_DELETED, False):
                                to_remove_indexes.append(run_index)
                                break
                            run_input.pop(cls.CONFIG_DELETED)
                    else:
                        runs.remove(run_data)
                for index in reversed(to_remove_indexes):
                    runs.pop(index)
                # ensure runs are a dict
                updated_queue[cls.CONFIG_RUNS] = {
                    index: run
                    for index, run in enumerate(runs)
                }
                # replace queue by updated one to keep order
                query = await writer_reader.search()
                if runs and runs[0]:
                    await writer_reader.update(cls.RUN_SCHEDULE_TABLE, updated_queue,
                                               query.id == updated_queue["id"])
                else:
                    await writer_reader.delete(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue["id"])
            except IndexError as e:
                # optimizer run not in db anymore
                pass
            return updated_queue

    async def _synchronized_pick_run(self, run_queue, run_details_by_hash):
        try:
            # acquire MultiprocessingLocks.DBLock to wait for re-ordering if it happens during a run
            with multiprocessing_util.get_lock(commons_enums.MultiprocessingLocks.DBLock.value):
                # wait for a very short  time to allow queue sync between processes
                selected_run_hash = run_queue.get(timeout=1)
            run_details = run_details_by_hash.pop(selected_run_hash, None)
            self.logger.info(f"Selecting: {run_details}")
            return selected_run_hash, run_details
        except queue.Empty:
            raise NoMoreRunError("Nothing to run")
        except Exception as e:
            self.logger.exception(e)

    async def run_single_iteration(self,
                                   optimizer_id,
                                   run_queues,
                                   run_data_by_hash,
                                   run_data,
                                   data_files,
                                   start_timestamp=None,
                                   end_timestamp=None):
        run_details = selected_run_hash = None
        start_run = False
        if run_data and run_data[0][self.CONFIG_RUNS]:
            selected_run_hash, run_details = await self._synchronized_pick_run(run_queues[self.START_QUEUE_KEY],
                                                                               run_data_by_hash)
        if run_details:
            # start backtesting run ids at 1
            backtesting_run_id = 1
            # always ensure backtesting id is unique
            run_dbs_identifier = databases.RunDatabasesIdentifier(
                self.trading_mode, self.optimization_campaign_name,
                optimizer_id=optimizer_id, backtesting_id=backtesting_run_id
            )
            # acquire MultiprocessingLocks.DBLock to avoid conflicts during multi processing runs
            with multiprocessing_util.get_lock(commons_enums.MultiprocessingLocks.DBLock.value):
                backtesting_run_id = await run_dbs_identifier.generate_new_backtesting_id()
                run_dbs_identifier.backtesting_id = backtesting_run_id
                await run_dbs_identifier.initialize()
            start_run = True
        if start_run:
            try:
                run_result = await self._run_with_config(optimizer_id, data_files, backtesting_run_id, run_details,
                                                         start_timestamp=start_timestamp, end_timestamp=end_timestamp)
                return run_result
            finally:
                if selected_run_hash is not None:
                    run_queues[self.DONE_QUEUE_KEY].put(selected_run_hash)
        raise NoMoreRunError("Nothing to run")

    async def _run_with_config(self, optimizer_id, data_files, run_id, run_config,
                               start_timestamp=None, end_timestamp=None):
        self.logger.debug(f"Running optimizer with id {optimizer_id} "
                          f"on backtesting {run_id} with config {run_config}")
        self._update_config_for_optimizer(optimizer_id, run_id)
        tentacles_setup_config = self._get_custom_tentacles_setup_config(optimizer_id, run_id, run_config)
        independent_backtesting = None
        try:
            import octobot.api.backtesting as octobot_backtesting_api
            # reset possible remaining caches
            await databases.CacheManager().reset()
            config_to_use = copy.deepcopy(self.config)
            independent_backtesting = octobot_backtesting_api.create_independent_backtesting(
                config_to_use,
                tentacles_setup_config,
                data_files,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                enforce_total_databases_max_size_after_run=False,
            )
            await octobot_backtesting_api.initialize_and_run_independent_backtesting(independent_backtesting,
                                                                                     log_errors=False)
            await octobot_backtesting_api.join_independent_backtesting(independent_backtesting, timeout=None)
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

    def _updated_nested_tentacle_config(self, nested_tentacles, user_input, config_value, local_tentacle_config):
        cleaned_tentacle_name = nested_tentacles[0].replace(" ", "_")
        if cleaned_tentacle_name not in local_tentacle_config:
            local_tentacle_config[cleaned_tentacle_name] = {}
        if len(nested_tentacles) == 1:
            local_tentacle_config[cleaned_tentacle_name][user_input.replace(" ", "_")] = config_value
        else:
            self._updated_nested_tentacle_config(nested_tentacles[1:], user_input, config_value,
                                                 local_tentacle_config[cleaned_tentacle_name])

    def _get_custom_tentacles_setup_config(self, optimizer_id, run_id, run_config):
        local_tentacles_setup_config = copy.deepcopy(self.base_tentacles_setup_config)
        run_dbs_identifier = databases.RunDatabasesIdentifier(
            self.trading_mode, self.optimization_campaign_name, optimizer_id=optimizer_id, backtesting_id=run_id)
        run_folder = run_dbs_identifier.get_backtesting_run_folder()
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
            self._updated_nested_tentacle_config(input_config[self.CONFIG_TENTACLE],
                                                 input_config[self.CONFIG_USER_INPUT],
                                                 input_config[self.CONFIG_VALUE],
                                                 tentacles_updates)
        self._ensure_local_config_folders(run_folder)
        for tentacle, updated_values in tentacles_updates.items():
            tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle)
            current_config = tentacles_manager_api.get_tentacle_config(self.base_tentacles_setup_config,
                                                                       tentacle_class)
            dict_util.nested_update_dict(current_config, updated_values)
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

    async def _generate_and_store_backtesting_runs_schedule(self):
        runs = self._generate_runs()
        await self._save_run_schedule(runs)
        return runs

    def _shuffle_and_select_runs(self, runs, select_size=None) -> dict:
        shuffled_runs = list(runs.values())
        random.shuffle(shuffled_runs)
        selected_runs = shuffled_runs if select_size is None else shuffled_runs[:select_size]
        return {i: run for i, run in enumerate(selected_runs)}

    def _generate_runs(self):
        iterations = [i for i in self._get_config_possible_iterations() if i]
        runs = {
            index: run
            for index, run in enumerate(itertools.product(*iterations))
            if self._is_run_allowed(run)
        }
        if runs:
            for run in self._shuffle_and_select_runs(runs, select_size=self.queue_size).values():
                for run_input in run:
                    # do not store self.CONFIG_KEY
                    run_input.pop(self.CONFIG_KEY, None)
            return runs
        raise RuntimeError("No optimizer run to schedule with this configuration")

    def _is_run_allowed(self, run):
        for run_filter_config in self.optimizer_config[self.CONFIG_FILTER_SETTINGS]:
            if self._is_filtered(run, run_filter_config):
                return False
        return True

    def _is_filtered(self, run, run_filter_config):
        left_operand, operator, right_operand = self._parse_filter_entry(run, run_filter_config)
        if not (left_operand and right_operand):
            return False
        try:
            left_operand = decimal.Decimal(left_operand)
        except decimal.InvalidOperation:
            left_operand = str(left_operand)
        try:
            right_operand = decimal.Decimal(right_operand)
        except decimal.InvalidOperation:
            right_operand = str(right_operand)
        return logical_operators.evaluate_condition(left_operand, right_operand, operator)

    def _parse_filter_entry(self, run, run_filter_config):
        user_input_left_operand_key = run_filter_config["user_input_left_operand"][self.CONFIG_VALUE]
        user_input_right_operand_key = run_filter_config["user_input_right_operand"][self.CONFIG_VALUE]

        left_operand = user_input_right_operand = None
        text_right_operand = run_filter_config["text_right_operand"][self.CONFIG_VALUE]
        operator = run_filter_config["operator"][self.CONFIG_VALUE]
        for user_input in run:
            if user_input[self.CONFIG_KEY] == user_input_left_operand_key:
                left_operand = user_input[self.CONFIG_VALUE]
            if user_input[self.CONFIG_KEY] == user_input_right_operand_key:
                user_input_right_operand = user_input[self.CONFIG_VALUE]
        right_operand = user_input_right_operand if text_right_operand in ("null", "") else text_right_operand
        return left_operand, operator, right_operand

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
                    addition = 1 if config[self.CONFIG_STEP] > 1 else config[self.CONFIG_STEP]
                    # Add 1 or step to max to include the max value in generated interval
                    values = [v.item()
                              for v in numpy.arange(config[self.CONFIG_MIN],
                                                    config[self.CONFIG_MAX] + addition,
                                                    config[self.CONFIG_STEP])
                              if v.item() <= config[self.CONFIG_MAX]]
            return [
                {
                    self.CONFIG_USER_INPUT: config_element[self.CONFIG_USER_INPUT],
                    self.CONFIG_TENTACLE: config_element[self.CONFIG_VALUE][self.CONFIG_TENTACLE]
                        .split(self.CONFIG_NESTED_TENTACLE_SEPARATOR),
                    self.CONFIG_VALUE: value,
                    self.CONFIG_KEY: config_element[self.CONFIG_KEY]
                }
                for value in values
            ]
        except ZeroDivisionError as e:
            raise ZeroDivisionError("Step value has to be greater than 0") from e

    def _get_config_elements(self):
        for key, val in self.optimizer_config[self.CONFIG_USER_INPUTS].items():
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
            self.CONFIG_ID: self.optimizer_id
        }
        self.total_nb_runs = len(runs)
        async with databases.DBWriterReader.database(self.run_dbs_identifier.get_optimizer_runs_schedule_identifier(),
                                                     with_lock=True) as writer_reader:
            try:
                existing_runs = await self._get_run_data_from_db(self.optimizer_id, writer_reader)
                if existing_runs:
                    merged_runs = {
                        self.get_run_hash(run_data): run_data
                        for run_data in existing_runs[0][self.CONFIG_RUNS].values()
                        if run_data
                    }
                    merged_runs.update({
                        self.get_run_hash(run_data): run_data
                        for run_data in self.runs_schedule[self.CONFIG_RUNS].values()
                        if run_data
                    })
                    self.runs_schedule[self.CONFIG_RUNS] = {
                        f"{index}": details
                        for index, details in enumerate(merged_runs.values())
                    }
                    await writer_reader.delete(self.RUN_SCHEDULE_TABLE, (await writer_reader.search()).id ==
                                               self.optimizer_id)
                await writer_reader.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
            except json.JSONDecodeError:
                self.logger.error(f"Invalid data in run schedule, clearing runs.")
                # error in database, reset it
                await writer_reader.hard_reset()
                await writer_reader.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
