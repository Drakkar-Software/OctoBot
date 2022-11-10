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
import math

import octobot.strategy_optimizer.scored_run_result as scored_run_result
import octobot.strategy_optimizer.optimizer_settings as optimizer_settings_import
import octobot.strategy_optimizer.optimizer_filter as optimizer_filter
import octobot.enums as enums
import octobot_commons.optimization_campaign as optimization_campaign
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging
import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_commons.databases as databases
import octobot_commons.dict_util as dict_util
import octobot_backtesting.errors as backtesting_errors
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_services.api as services_api
import octobot_services.enums as services_enums
import octobot_trading.constants as trading_constants


class ConfigTypes(enum.Enum):
    NUMBER = "number"
    BOOLEAN = "boolean"
    OPTIONS = "options"
    UNKNOWN = "unknown"


class NoMoreRunError(Exception):
    pass


class StrategyDesignOptimizer:
    SHARED_KEEP_RUNNING_KEY = "keep_running"
    SHARED_RUN_TIMES_KEY = "run_times"
    SHARED_RUNS_QUEUES_KEY = "runs_queues"
    START_QUEUE_KEY = "start_queue"
    DONE_QUEUE_KEY = "done_queue"

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

    def __init__(self, trading_mode, config, tentacles_setup_config, optimizer_settings=None):
        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.config = config
        self.base_tentacles_setup_config = tentacles_setup_config
        self.trading_mode = trading_mode
        self.optimizer_settings: optimizer_settings_import.OptimizerSettings = \
            optimizer_settings or optimizer_settings_import.OptimizerSettings()
        self.current_backtesting_id = None
        self.runs_schedule = None
        self.optimization_campaign_name = optimization_campaign.OptimizationCampaign.get_campaign_name(
            tentacles_setup_config
        )
        self.run_dbs_identifier = databases.RunDatabasesIdentifier(self.trading_mode, self.optimization_campaign_name)

        self.is_computing = False
        self.is_finished = False
        self.total_nb_runs = 0
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

    async def _create_run_queues(self, optimizer_id, run_data):
        run_data_by_hash = self._get_optimizer_runs_details_and_hashes(run_data) if run_data \
            else await self._read_optimizer_runs_details_and_hashes(optimizer_id)
        start_queue = multiprocessing.Queue(len(run_data_by_hash))
        done_queue = multiprocessing.Queue(len(run_data_by_hash))
        for run_hash in run_data_by_hash:
            start_queue.put(run_hash)
        return {
            self.START_QUEUE_KEY: start_queue,
            self.DONE_QUEUE_KEY: done_queue
        }

    async def multi_processed_optimize(self, optimizer_settings, run_data_by_optimizer_id=None):
        success = True
        optimizer_ids = optimizer_settings.optimizer_ids or [optimizer_settings.optimizer_id]
        run_data_by_optimizer_id = run_data_by_optimizer_id or {}
        self.is_computing = True
        self.is_finished = False
        self.average_run_time = 0
        self.active_processes_count = multiprocessing.cpu_count() - abs(optimizer_settings.required_idle_cores)
        self.total_nb_runs = await self._get_total_nb_runs(optimizer_ids)
        global_t0 = time.time()
        lock = multiprocessing.RLock()
        shared_keep_running = multiprocessing.Value(ctypes.c_bool, True)
        shared_run_time = multiprocessing.Array(ctypes.c_float, [0.0 for _ in range(self.active_processes_count)])
        try:
            async for selected_optimizer_ids in self._all_optimizer_ids(optimizer_ids,
                                                                        optimizer_settings.empty_the_queue):
                run_queues_by_optimizer_id = {
                    optimizer_id: await self._create_run_queues(optimizer_id,
                                                                run_data_by_optimizer_id.get(optimizer_id))
                    for optimizer_id in selected_optimizer_ids
                }
                try:
                    await self._run_multi_processed_optimizer(
                        optimizer_settings, lock,
                        shared_keep_running, shared_run_time,
                        run_queues_by_optimizer_id
                    )
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
            success = False
        finally:
            if optimizer_settings.notify_when_complete:
                await self._send_optimizer_finished_notification()
            self.process_pool_handle = None
            self.is_computing = False
            self.is_finished = True
        self.logger.info(f"Optimizer runs complete in {time.time() - global_t0} seconds.")
        return success

    async def _run_multi_processed_optimizer(self, optimizer_settings,
                                             lock, shared_keep_running, shared_run_time,
                                             run_queues_by_optimizer_id):
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
                idle_cores_message = f"Requiring to leave {optimizer_settings.required_idle_cores} idle core. " \
                    if optimizer_settings.required_idle_cores else ""
                raise RuntimeError(f"{idle_cores_message}At lease one core is required to "
                                   f"start a strategy optimizer. "
                                   f"There are {multiprocessing.cpu_count()} total available cores on this computer.")
            for index in range(self.active_processes_count):
                coros.append(
                    asyncio.get_event_loop().run_in_executor(
                        pool,
                        self.find_optimal_configuration_wrapper,
                        optimizer_settings.data_files,
                        index == 0,
                        optimizer_settings.start_timestamp,
                        optimizer_settings.end_timestamp
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

    async def _read_optimizer_runs_details_and_hashes(self, optimizer_id):
        async with databases.DBReader.database(self.run_dbs_identifier.get_optimizer_runs_schedule_identifier()) \
                as reader:
            run_data = await self._get_run_data(optimizer_id, reader)
        try:
            return self._get_optimizer_runs_details_and_hashes(run_data[0][self.CONFIG_RUNS])
        except IndexError:
            raise NoMoreRunError

    def _get_optimizer_runs_details_and_hashes(self, run_data):
        if run_data:
            return {
                self.get_run_hash(run_details): run_details
                for run_details in run_data.values()
            }
        raise NoMoreRunError

    async def _execute_optimizer_run(self, optimizer_id, run_queues, update_database, data_files,
                                     start_timestamp, end_timestamp):
        if update_database and optimizer_id is None:
            # should not happen but in case it does, drop the run
            await self.drop_optimizer_run_from_queue(optimizer_id)
            return
        try:
            run_data_by_hash = await self._read_optimizer_runs_details_and_hashes(optimizer_id)
            t_start = time.time()
            last_db_update_time = t_start
            while self._should_keep_running():
                await self.run_single_iteration(optimizer_id,
                                                run_queues,
                                                run_data_by_hash,
                                                data_files,
                                                start_timestamp=start_timestamp,
                                                end_timestamp=end_timestamp)
                if self.first_iteration_time == 0:
                    self.first_iteration_time = time.time() - t_start
                    self._register_run_time(self.first_iteration_time)
                if update_database and time.time() - last_db_update_time > self.optimizer_settings.db_update_period:
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
                       if optimizer_id in optimizer_ids or self.optimizer_settings.empty_the_queue)
        except KeyError:
            return 0

    async def get_overall_progress(self):
        if self.optimizer_settings.optimizer_id is None:
            remaining_runs = await self._get_remaining_runs_count_from_multi_process_queue(
                self.optimizer_settings.optimizer_ids)
        else:
            remaining_runs = await self._get_remaining_runs_count_from_multi_process_queue(
                self.optimizer_settings.optimizer_id)
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

    async def _get_run_data(self, optimizer_id, reader):
        if self.runs_schedule:
            return [self.runs_schedule]
        return await self._get_run_data_from_db(optimizer_id, reader)

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

    async def resume(self, optimizer_settings: optimizer_settings_import.OptimizerSettings):
        self.total_nb_runs = await self._get_total_nb_runs(optimizer_settings.optimizer_ids)
        if optimizer_settings.optimizer_mode == enums.OptimizerModes.GENETIC.value:
            return await self._launch_automated_optimization(optimizer_settings)
        elif optimizer_settings.optimizer_mode == enums.OptimizerModes.NORMAL.value:
            return await self.multi_processed_optimize(optimizer_settings)
        else:
            raise NotImplementedError(f"Unknown optimizer mode: {optimizer_settings.optimizer_mode}")

    async def _launch_automated_optimization(self, optimizer_settings):
        notify_when_complete = optimizer_settings.notify_when_complete
        # do not notify after each campaign
        optimizer_settings.notify_when_complete = False
        # only use first optimizer id
        optimizer_id = optimizer_settings.optimizer_ids[0]
        optimizer_settings.optimizer_ids = [optimizer_id]
        relevant_fitness_parameters = copy.deepcopy(self.optimizer_settings.fitness_parameters)
        exclude_filters = copy.deepcopy(self.optimizer_settings.exclude_filters)
        self.logger.info(f"Launching initial generation with a pool of "
                         f"{optimizer_settings.initial_generation_count} runs")
        generation_run_data = \
            await self._generate_first_generation_run_data(optimizer_id, optimizer_settings.initial_generation_count)
        already_run_index = len(generation_run_data)
        success = True
        try:
            for generation_id in range(optimizer_settings.generations_count):
                # 1. run current generation
                if not await self.multi_processed_optimize(
                    optimizer_settings,
                    run_data_by_optimizer_id={
                        optimizer_id: {
                            index: value
                            for index, value in generation_run_data.items()
                            if index <= already_run_index
                        }
                    },
                ):
                    raise Exception("Unexpected error when running optimizer")
                # 2. score results (fitness function)
                all_run_results = await self._get_all_finished_run_results(optimizer_id)
                self._format_user_inputs_names(all_run_results)
                filtered_run_results = [
                    run_result
                    for run_result in all_run_results
                    if not self._is_excluded(run_result, exclude_filters)
                ]
                if len(filtered_run_results) < 2:
                    self.logger.info(f"Not enough runs to generate a next generation after filtering results. "
                                     f"{len(all_run_results)} results before filters "
                                     f"and {len(filtered_run_results)} after filters. "
                                     f"At least 2 results after filters are required to create the next generation.")
                    raise NoMoreRunError
                current_generation_results = await self._score_current_generation(generation_run_data,
                                                                                  filtered_run_results,
                                                                                  relevant_fitness_parameters)
                formatted_results = "\n".join([
                    f"{i + 1} - {run_result.result_str()}"
                    for i, run_result in enumerate(current_generation_results)
                ])
                self.logger.info(f"Generation {generation_id + 1} top run results:\n{formatted_results}")
                self._check_target_fitness(optimizer_settings.target_fitness_score, current_generation_results)
                # 3. create next generation (crossover and mutation)
                generation_run_data, already_run_index = await self._create_next_generation(
                    optimizer_settings,
                    current_generation_results,
                    filtered_run_results,
                    generation_id
                )
                # 4. update self.runs_schedule
                self.runs_schedule = {
                    self.CONFIG_RUNS: {
                        index: value
                        for index, value in generation_run_data.items()
                    }
                }
        except NoMoreRunError:
            # nothing left to optimize
            pass
        except Exception as e:
            self.logger.exception(e, True, "Unexpected error when running optimizer: {e}")
            success = False
        self.logger.info("Optimizer complete")
        if notify_when_complete:
            await self._send_optimizer_finished_notification()
        return success

    def _format_user_inputs_names(self, run_results):
        for run_result in run_results:
            for tentacle_user_inputs in run_result[commons_enums.BacktestingMetadata.USER_INPUTS.value].values():
                for key in list(tentacle_user_inputs):
                    tentacle_user_inputs[key.replace(" ", "_")] = tentacle_user_inputs[key]

    def _check_target_fitness(self, target_fitness_score, results):
        if target_fitness_score is None:
            return
        for result in results:
            if result.score >= target_fitness_score:
                self.logger.info(f"The target fitness score of {target_fitness_score} has been reached.")
                raise NoMoreRunError

    async def _score_current_generation(self, generation_run_data, all_run_results, relevant_fitness_parameters):
        # 1. update ratio dependent fitness score
        for fitness_param in relevant_fitness_parameters:
            if fitness_param.is_ratio_from_max:
                for run_data, run_data_from_results in self._get_from_run_results(generation_run_data, all_run_results):
                    fitness_param.update_ratio(run_data_from_results)
        # 2. find results of generation_run_data
        run_results = [
            scored_run_result.ScoredRunResult(
                run_data_from_results,
                run_data
            )
            for run_data, run_data_from_results in self._get_from_run_results(generation_run_data, all_run_results)
        ]
        # 3 compute score
        for run_result in run_results:
            run_result.compute_score(relevant_fitness_parameters)
        return sorted(run_results, key=lambda r: r.score, reverse=True)

    def _get_from_run_results(self, run_data_elements, all_run_results):
        if all_run_results:
            yielded_count = 1
            for run_data_from_runs in reversed(all_run_results):
                for to_find_run_data in run_data_elements.values():
                    if self._is_using_these_user_inputs(
                            run_data_from_runs,
                            to_find_run_data
                    ):
                        yield to_find_run_data, run_data_from_runs
                        if yielded_count == len(run_data_elements):
                            return
                        yielded_count += 1

    async def _get_all_finished_run_results(self, optimizer_id):
        db_identifier = databases.RunDatabasesIdentifier(
            self.trading_mode, self.optimization_campaign_name,
            optimizer_id=optimizer_id
        )
        async with databases.DBReader.database(db_identifier.get_backtesting_metadata_identifier()) as reader:
            return await reader.all(commons_enums.DBTables.METADATA.value)

    def _is_using_these_user_inputs(self, full_run_data, to_find_run_data):
        full_run_data_user_inputs = full_run_data[commons_enums.BacktestingMetadata.USER_INPUTS.value]
        for user_input_data in to_find_run_data:
            try:
                # todo handle user input with object config
                if full_run_data_user_inputs[user_input_data[self.CONFIG_TENTACLE][0]] \
                        [user_input_data[self.CONFIG_USER_INPUT]] != user_input_data[self.CONFIG_VALUE]:
                    return False
            except KeyError:
                return False
        return True

    def _is_excluded(self, run_result, exclude_filters):
        for exclude_filter in exclude_filters:
            exclude_filter.load_values(run_result)
            if exclude_filter.is_filtered():
                return True
        return False

    async def _create_next_generation(
            self,
            optimizer_settings,
            current_generation_results,
            all_run_results,
            generation_id
    ):
        mutations_count = int(optimizer_settings.run_per_generation * optimizer_settings.mutation_percent / 100)
        crossovers_count = int(optimizer_settings.run_per_generation - mutations_count)
        new_generation = []
        # 0. init ui config
        for parent in current_generation_results:
            for ui_element in parent.optimizer_run_data:
                _, ui_element[self.CONFIG_KEY] = self._get_ui_config(ui_element)
        # 1. crossover
        best_parents_pairs = self._get_score_sorted_pairs(current_generation_results)
        for left_parent, right_parent in best_parents_pairs:
            new_generation.append(self._crossover(left_parent, right_parent))
            # avoid duplicate children
            new_generation = self._remove_duplicate(new_generation)
            if len(new_generation) >= crossovers_count + mutations_count:
                break
        self.logger.info(f"Generated {len(new_generation)} new runs based on top previous runs")
        # 2. mutations
        start_mutations_index = crossovers_count
        if len(new_generation) < crossovers_count + mutations_count:
            mutations_count = int(len(new_generation) * optimizer_settings.mutation_percent / 100)
            start_mutations_index = len(new_generation) - mutations_count
        mutations_count = 0
        mutation_intensity = self._get_mutation_multiplier(generation_id, optimizer_settings.generations_count)
        for run_data in new_generation[start_mutations_index:]:
            mutations_count += \
                self._mutate(optimizer_settings, run_data, mutation_intensity)
        self.logger.info(f"Added mutations to {mutations_count} of the generated runs")
        # 3. filter invalid configurations according to filters and already run configurations
        filtered_new_generation = self._filter_generation(new_generation, all_run_results)
        self.logger.info(f"Filtered {len(new_generation) - len(filtered_new_generation)} already run configurations")
        if len(filtered_new_generation) == 0:
            # nothing else to run, stop optimization
            self.logger.info(f"No more run to generate")
            raise NoMoreRunError
        formatted_new_generation = "\n".join([
            "-" + str(
                {
                    ui[StrategyDesignOptimizer.CONFIG_USER_INPUT]: ui[StrategyDesignOptimizer.CONFIG_VALUE]
                    for ui in run
                }
            )
            for run in filtered_new_generation
        ])
        self.logger.info(f"Evaluating new generation of {len(filtered_new_generation)} elements :"
                         f"\n{formatted_new_generation}")
        new_generation = filtered_new_generation
        # 4. add parents to retain the same amounts to compare and mutate in next generation
        already_run_index = len(new_generation) - 1
        new_generation += [
            result.optimizer_run_data
            for result in current_generation_results[:optimizer_settings.run_per_generation]
        ]
        # 5. return new generation
        return {i: element for i, element in enumerate(new_generation)}, already_run_index

    def _get_score_sorted_pairs(self, elements):
        scored_elements = [
            ((element_1.score + element_2.score) / 2, (element_1, element_2))
            for element_1, element_2 in itertools.combinations(elements, 2)
        ]
        scored_elements.sort(key=lambda x: x[0], reverse=True)    # sort by parents combined score
        return [
            scored_element[1]
            for scored_element in scored_elements
        ]

    def _filter_generation(self, generation, all_run_results):
        # remove invalid configurations according to user defined filters
        # remove already run configurations
        not_ran_elements = [
            element
            for element in generation
            if self._is_run_allowed(element) and not self._is_already_run(element, all_run_results)
        ]
        # remove duplicated in generation
        return self._remove_duplicate(not_ran_elements)

    def _remove_duplicate(self, run_data_elements):
        return list(
            {
                self.get_run_hash(element): element
                for element in run_data_elements
            }.values()
        )

    def _is_already_run(self, element, all_run_results):
        try:
            # create temp dict to keep the same interface
            next(iter(self._get_from_run_results({None: element}, all_run_results)))
            return True
        except StopIteration:
            return False

    def _crossover(self, parent_1, parent_2):
        child_ui_data_elements = []
        for parent_1_ui_data, parent_2_ui_data in zip(parent_1.optimizer_run_data, parent_2.optimizer_run_data):
            child_ui_data_element = copy.deepcopy(parent_1_ui_data)
            ui_config, _ = self._get_ui_config(child_ui_data_element)
            child_ui_data_element[self.CONFIG_VALUE] = self._get_child_value(
                parent_1_ui_data,
                parent_2_ui_data,
                ui_config
            )
            child_ui_data_elements.append(child_ui_data_element)
        return child_ui_data_elements

    def _mutate(self, optimizer_settings, run_data, mutation_intensity):
        # the closer to 1 is mutation_intensity, the stronger the mutations
        intensity_multiplier = \
            mutation_intensity + (optimizer_settings.min_mutation_probability_percent / trading_constants.ONE_HUNDRED)
        mutation_trigger_threshold = \
            optimizer_settings.max_mutation_probability_percent / \
            ((trading_constants.ONE_HUNDRED + optimizer_settings.min_mutation_probability_percent)
             / trading_constants.ONE_HUNDRED)
        mutated = False
        for ui_element in run_data:
            if random.randint(0, 100) <= intensity_multiplier * mutation_trigger_threshold:
                self._mutate_element(optimizer_settings, ui_element, mutation_intensity)
                mutated = True
        return mutated

    def _get_mutation_multiplier(self, generation_number, total_generations):
        linear_intensity = decimal.Decimal(str(1 - generation_number / total_generations))
        exp_intensity = pow(linear_intensity, 2)
        return exp_intensity

    def _mutate_element(self, optimizer_settings, ui_element, mutation_intensity):
        ui_config, _ = self._get_ui_config(ui_element)
        ui_type = self._get_config_type(ui_config)
        ui_constraint = optimizer_settings.get_constraint(ui_element[self.CONFIG_KEY])
        if ui_type is ConfigTypes.NUMBER:
            # mutate numbers
            min_val, max_val, step = self._get_number_config(ui_config)
            stay_within_boundaries = optimizer_settings.stay_within_boundaries
            if ui_constraint is not None:
                stay_within_boundaries = True
                if not ui_constraint.stay_within_boundaries:
                    min_val = ui_constraint.min_val
                    max_val = ui_constraint.max_val
            d_min_val = decimal.Decimal(str(min_val))
            d_max_val = decimal.Decimal(str(max_val))
            mutation_max_delta = (d_max_val - d_min_val) * optimizer_settings.max_mutation_number_multiplier \
                * mutation_intensity
            # use exponential multiplier to get more often results around 1 and use the max delta more often
            exp_random_multiplier = decimal.Decimal(math.sqrt(random.random()))
            new_value = decimal.Decimal(str(ui_element[self.CONFIG_VALUE])) + \
                        (mutation_max_delta * exp_random_multiplier)
            if stay_within_boundaries:
                if new_value < d_min_val:
                    new_value = d_min_val
                elif new_value > d_max_val:
                    new_value = d_max_val
            # apply the right type to the new value
            target_type = self._get_accurate_number_type(min_val, max_val, step)
            mutated_value = self._get_typed_value(new_value, target_type)
            ui_element[self.CONFIG_VALUE] = mutated_value

    def _get_child_value(self, parent_1_ui, parent_2_ui, ui_config):
        value_1 = parent_1_ui[self.CONFIG_VALUE]
        value_2 = parent_2_ui[self.CONFIG_VALUE]
        if type(value_1) != type(value_2):
            raise TypeError(f"{value_1} and {value_2} have a different type")
        ui_type = self._get_config_type(ui_config)
        if ui_type in (ConfigTypes.OPTIONS, ConfigTypes.BOOLEAN):
            # on options and booleans, don't generate values, use a parent value
            return value_1 if random.randint(0, 1) == 1 else value_2
        if ui_type is ConfigTypes.NUMBER:
            min_val, max_val, step = self._get_number_config(ui_config)
            # on numbers, generate a value between parents taking step into account
            child_value = (decimal.Decimal(str(value_1)) + decimal.Decimal(str(value_2))) / decimal.Decimal(2)
            # ensure step is taken into account
            normalized_value = child_value - decimal.Decimal(str(min_val))
            decimal_step = decimal.Decimal(str(step))
            normalized_mod = normalized_value % decimal_step
            target_type = self._get_accurate_number_type(min_val, max_val, step)
            if normalized_mod == 0:
                return self._get_typed_value(child_value, target_type)
            # find the closest valid value
            to_add_val = decimal_step - normalized_mod
            if normalized_mod < decimal_step / decimal.Decimal(2):
                to_add_val = -to_add_val
            # apply the right type to the new value
            return self._get_typed_value(child_value + to_add_val, target_type)
        raise TypeError(f"unsupported config type: {ui_type}")

    def _get_typed_value(self, initial_value, target_type):
        if target_type is int:
            # round up or down with a 50% chance
            if random.random() <= 0.5:
                return math.ceil(initial_value)
            return math.floor(initial_value)
        return target_type(initial_value)

    async def _generate_first_generation_run_data(self, optimizer_id,
                                                  automated_initial_optimization_run_count):
        async with databases.DBReader.database(self.run_dbs_identifier.get_optimizer_runs_schedule_identifier()) \
                as reader:
            run_data = await self._get_run_data(optimizer_id, reader)
        return self.shuffle_and_select_runs(run_data[0][self.CONFIG_RUNS],
                                            select_size=automated_initial_optimization_run_count)

    async def _send_optimizer_finished_notification(self):
        await services_api.send_notification(
            services_api.create_notification(f"Your strategy optimizer just finished.",
                                             sound=services_enums.NotificationSound.FINISHED_PROCESSING,
                                             category=services_enums.NotificationCategory.OTHER)
        )

    async def _get_total_nb_runs(self, optimizer_ids):
        full_queue = await self.get_run_queue(self.trading_mode)
        if self.optimizer_settings.empty_the_queue:
            return sum(len(run[self.CONFIG_RUNS]) for run in full_queue)
        return sum(len(run[self.CONFIG_RUNS]) for run in full_queue if run[self.CONFIG_ID] in optimizer_ids)

    async def generate_and_save_run(self):
        taken_ids = await self.get_queued_optimizer_ids()
        self.optimizer_settings.optimizer_id = await self.run_dbs_identifier.generate_new_optimizer_id(taken_ids) \
            if self.optimizer_settings.optimizer_id is None else self.optimizer_settings.optimizer_id
        self.run_dbs_identifier.optimizer_id = self.optimizer_settings.optimizer_id
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
                        (await writer_reader.select(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue[cls.CONFIG_ID]))[
                            0]
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
                                   data_files,
                                   start_timestamp=None,
                                   end_timestamp=None):
        start_run = False
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

    @staticmethod
    def shuffle_and_select_runs(runs, select_size=None) -> dict:
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
            shuffled_runs = self.shuffle_and_select_runs(runs, select_size=self.optimizer_settings.queue_size)
            for run in shuffled_runs.values():
                for run_input in run:
                    # do not store self.CONFIG_KEY
                    run_input.pop(self.CONFIG_KEY, None)
            return shuffled_runs
        raise RuntimeError("No optimizer run to schedule with this configuration")

    def _is_run_allowed(self, run):
        for run_filter_config in self.optimizer_settings.optimizer_config[self.CONFIG_FILTER_SETTINGS]:
            if self._is_filtered(run, run_filter_config):
                return False
        return True

    def _is_filtered(self, run, run_filter_config):
        operator_filter = self._parse_filter_entry(run, run_filter_config)
        return operator_filter.is_filtered()

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
        return optimizer_filter.OptimizerFilter(user_input_left_operand_key, user_input_right_operand_key,
                                                left_operand, right_operand,
                                                operator)

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
                if config_element[self.CONFIG_TYPE] is ConfigTypes.OPTIONS:
                    values = [[value] for value in config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]]
                if config_element[self.CONFIG_TYPE] is ConfigTypes.BOOLEAN:
                    values = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
                if config_element[self.CONFIG_TYPE] is ConfigTypes.NUMBER:
                    config = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
                    values = [v
                              for v in self._get_all_possible_values(config[self.CONFIG_MIN],
                                                                     config[self.CONFIG_MAX],
                                                                     config[self.CONFIG_STEP])
                              if v <= config[self.CONFIG_MAX]]
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

    def _get_all_possible_values(self, start, stop, step):
        # use custom decimal function for precision instead of numpy.arange
        d_start = decimal.Decimal(str(start))
        d_stop = decimal.Decimal(str(stop))
        d_step = decimal.Decimal(str(step))
        return_type = self._get_accurate_number_type(start, stop, step)
        current = d_start
        while current <= d_stop:
            yield return_type(current)
            current += d_step

    def _get_accurate_number_type(self, *values):
        return int if all(isinstance(e, int) for e in values) else float

    def _get_config_elements(self):
        for key, val in self.optimizer_settings.optimizer_config[self.CONFIG_USER_INPUTS].items():
            yield {
                self.CONFIG_KEY: key,
                self.CONFIG_ENABLED: val[self.CONFIG_ENABLED],
                self.CONFIG_USER_INPUT: val[self.CONFIG_USER_INPUT],
                self.CONFIG_VALUE: val,
                self.CONFIG_TYPE: self._get_config_type(val)
            }

    def _get_config_key(self, ui_element):
        # todo check
        return f"{ui_element[self.CONFIG_TENTACLE][0]}{self.CONFIG_NESTED_TENTACLE_SEPARATOR}" \
               f"{ui_element[self.CONFIG_USER_INPUT]}"

    def _get_ui_config(self, ui_element):
        try:
            # try using the self.CONFIG_KEY value element if ui_element
            return self.optimizer_settings.optimizer_config[self.CONFIG_USER_INPUTS][ui_element[self.CONFIG_KEY]], \
                   ui_element[self.CONFIG_KEY]
        except KeyError:
            pass
        for key, val in self.optimizer_settings.optimizer_config[self.CONFIG_USER_INPUTS].items():
            if self._is_user_input_config(val, ui_element):
                return val, key
        raise KeyError(ui_element[self.CONFIG_USER_INPUT])

    def _get_number_config(self, ui_config):
        config_val = ui_config[self.CONFIG_VALUE]
        return config_val[self.CONFIG_MIN], config_val[self.CONFIG_MAX], config_val[self.CONFIG_STEP]

    def _is_user_input_config(self, ui_config, ui_element):
        return ui_config[self.CONFIG_USER_INPUT] == ui_element[self.CONFIG_USER_INPUT] and \
               ui_config[self.CONFIG_TENTACLE] == ui_element[self.CONFIG_TENTACLE][-1]

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
            self.CONFIG_ID: self.optimizer_settings.optimizer_id
        }
        self.total_nb_runs = len(runs)
        async with databases.DBWriterReader.database(self.run_dbs_identifier.get_optimizer_runs_schedule_identifier(),
                                                     with_lock=True) as writer_reader:
            try:
                existing_runs = await self._get_run_data_from_db(self.optimizer_settings.optimizer_id, writer_reader)
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
                                               self.optimizer_settings.optimizer_id)
                await writer_reader.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
            except json.JSONDecodeError:
                self.logger.error(f"Invalid data in run schedule, clearing runs.")
                # error in database, reset it
                await writer_reader.hard_reset()
                await writer_reader.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
