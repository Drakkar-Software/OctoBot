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

    RUN_SCHEDULE_TABLE = "schedule"
    CONFIG_KEY = "key"
    CONFIG_USER_INPUT = "user_input"
    CONFIG_USER_INPUTS = "user_inputs"
    CONFIG_FILTER_SETTINGS = "filters_settings"
    CONFIG_VALUE = "value"
    CONFIG_TENTACLE = "tentacle"
    CONFIG_NESTED_TENTACLE_SEPARATOR = "_-_"
    CONFIG_TYPE = "type"
    CONFIG_ENABLED = "enabled"
    CONFIG_MIN = "min"
    CONFIG_MAX = "max"
    CONFIG_STEP = "step"
    CONFIG_RUNS = "runs"
    CONFIG_DATA_FILES = "data_files"
    CONFIG_ID = "id"
    CONFIG_DELETED = "deleted"
    CONFIG_ROLE = "role"

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
        self.optimization_campaign_name = optimization_campaign.OptimizationCampaign.get_campaign_name(
            tentacles_setup_config
        )
        self.database_manager = databases.DatabaseManager(self.trading_mode, self.optimization_campaign_name)

        self.is_computing = False
        self.current_run_id = 0
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

    def get_name(self) -> str:
        return f"{self.trading_mode.get_name()}_{self.__class__.__name__}"

    async def multi_processed_optimize(self,
                                       optimizer_ids=None,
                                       randomly_chose_runs=False,
                                       start_timestamp=None,
                                       end_timestamp=None,
                                       empty_the_queue=False,
                                       required_idle_cores=0,
                                       notify_when_complete=False):
        optimizer_ids = optimizer_ids or [self.optimizer_id]
        self.is_computing = True
        global_t0 = time.time()
        lock = multiprocessing.RLock()
        shared_keep_running = multiprocessing.Value(ctypes.c_bool, True)
        self.average_run_time = 0
        self.active_processes_count = multiprocessing.cpu_count() - abs(required_idle_cores)
        shared_run_time = multiprocessing.Array(ctypes.c_float, [0.0 for _ in range(self.active_processes_count)])
        try:
            self.current_run_id = 1
            with multiprocessing_util.registered_lock_and_shared_elements(
                    commons_enums.MultiprocessingLocks.DBLock.value,
                    lock,
                    {
                        self.SHARED_KEEP_RUNNING_KEY: shared_keep_running,
                        self.SHARED_RUN_TIMES_KEY: shared_run_time
                    }),\
                 concurrent.futures.ProcessPoolExecutor(
                    initializer=multiprocessing_util.register_lock_and_shared_elements,
                    initargs=(commons_enums.MultiprocessingLocks.DBLock.value,
                              lock,
                              {
                                  self.SHARED_KEEP_RUNNING_KEY: shared_keep_running,
                                  self.SHARED_RUN_TIMES_KEY: shared_run_time
                              })) as pool:
                coros = []
                self.logger.info(f"Dispatching optimizer backtesting runs into {self.active_processes_count} "
                                 f"parallel processes (based on the current computer physical processors).")
                if self.active_processes_count < 1:
                    idle_cores_message = f"Requiring to leave {required_idle_cores} idle core. " \
                        if required_idle_cores else ""
                    raise RuntimeError(f"{idle_cores_message}At lease one core is required to "
                                       f"start a strategy optimizer. "
                                       f"There are {pool._max_workers} total available cores on this computer.")
                for _ in range(self.active_processes_count):
                    coros.append(
                            asyncio.get_event_loop().run_in_executor(
                                pool,
                                self.find_optimal_configuration_wrapper,
                                optimizer_ids,
                                randomly_chose_runs,
                                start_timestamp,
                                end_timestamp,
                                empty_the_queue
                            )
                        )
                self.process_pool_handle = await asyncio.gather(*coros)
        except Exception as e:
            self.logger.exception(e, True, f"Error when running optimizer processes: {e}")
        finally:
            if notify_when_complete:
                await services_api.send_notification(
                    services_api.create_notification(f"Your strategy optimizer just finished.",
                                                     category=services_enums.NotificationCategory.OTHER)
                )
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

    def find_optimal_configuration_wrapper(self,
                                           optimizer_ids,
                                           randomly_chose_runs=False,
                                           start_timestamp=None,
                                           end_timestamp=None,
                                           empty_the_queue=False):
        self._init_optimizer_process_logger()
        asyncio.run(self.find_optimal_configuration(optimizer_ids,
                                                    randomly_chose_runs=randomly_chose_runs,
                                                    start_timestamp=start_timestamp,
                                                    end_timestamp=end_timestamp,
                                                    empty_the_queue=empty_the_queue))

    async def find_optimal_configuration(self,
                                         optimizer_ids,
                                         randomly_chose_runs=False,
                                         start_timestamp=None,
                                         end_timestamp=None,
                                         empty_the_queue=False):
        # need to load tentacles when in new process
        tentacles_manager_api.reload_tentacle_info()
        try:
            async for optimizer_id in self._all_optimizer_ids(optimizer_ids, empty_the_queue):
                await self._execute_optimizer_run(optimizer_id, randomly_chose_runs,
                                                  start_timestamp, end_timestamp)

        except concurrent.futures.CancelledError:
            self.logger.info("Cancelled run")
            raise

    async def _all_optimizer_ids(self, prioritized_ids, empty_the_queue):
        if prioritized_ids:
            for prioritized_id in prioritized_ids:
                yield prioritized_id
        if empty_the_queue:
            updated_ids = await self.get_queued_optimizer_ids()
            while self._should_keep_running() and updated_ids:
                # reselect from database in case new runs were added
                for optimizer_id in await self.get_queued_optimizer_ids():
                    yield optimizer_id
                updated_ids = await self.get_queued_optimizer_ids()

    async def _execute_optimizer_run(self, optimizer_id, randomly_chose_runs,
                                     start_timestamp, end_timestamp):
        if optimizer_id is None:
            # should not happen but in case it does, drop the run
            await self.drop_optimizer_run_from_queue(optimizer_id)
            return
        try:
            t_start = time.time()
            while self._should_keep_running():
                await self.run_single_iteration(optimizer_id,
                                                randomly_chose_runs=randomly_chose_runs,
                                                start_timestamp=start_timestamp,
                                                end_timestamp=end_timestamp)
                if self.first_iteration_time == 0:
                    self.first_iteration_time = time.time() - t_start
                    self._register_run_time(self.first_iteration_time)
        except NoMoreRunError:
            await self.drop_optimizer_run_from_queue(optimizer_id)

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
            run_times = [v for v in multiprocessing_util.get_shared_element(self.SHARED_RUN_TIMES_KEY)]
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

    async def _get_remaining_runs_count_from_db(self, optimizer_id):
        async with databases.DBReader.database(self.database_manager.get_optimizer_runs_schedule_identifier(),
                                               with_lock=True) as reader:
            run_data = await self._get_run_data_from_db(optimizer_id, reader)
        if run_data and run_data[0][self.CONFIG_RUNS]:
            return len(run_data[0][self.CONFIG_RUNS])
        return 0

    async def get_overall_progress(self):
        if self.optimizer_id is None:
            remaining_runs = await self._get_total_nb_runs(self.prioritized_optimizer_ids)
        else:
            remaining_runs = await self._get_remaining_runs_count_from_db(self.optimizer_id)
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

    async def resume(self, optimizer_ids, randomly_chose_runs,
                     start_timestamp=None,
                     end_timestamp=None,
                     empty_the_queue=False,
                     required_idle_cores=0,
                     notify_when_complete=False):
        self.empty_the_queue = empty_the_queue
        self.total_nb_runs = await self._get_total_nb_runs(optimizer_ids)
        self.prioritized_optimizer_ids = optimizer_ids
        await self.multi_processed_optimize(optimizer_ids=optimizer_ids,
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
        self.optimizer_id = await self.database_manager.generate_new_optimizer_id(taken_ids)
        self.database_manager.optimizer_id = self.optimizer_id
        await self.database_manager.initialize()
        return await self._generate_and_store_backtesting_runs_schedule()

    @classmethod
    async def get_run_queue(cls, trading_mode, campaign_name=None):
        campaign_name = campaign_name or optimization_campaign.OptimizationCampaign.get_campaign_name()
        db_manager = databases.DatabaseManager(trading_mode, campaign_name)
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
                        found_difference = False
                        for key, val in reference_run_input_details.items():
                            if key != cls.CONFIG_KEY and val != run_input_details[key]:
                                found_difference = True
                                break
                        if not found_difference:
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
        db_manager = databases.DatabaseManager(trading_mode,
                                               optimization_campaign.OptimizationCampaign.get_campaign_name())
        async with databases.DBWriterReader.database(db_manager.get_optimizer_runs_schedule_identifier(),
                                                     with_lock=True) as writer_reader:
            query = await writer_reader.search()
            try:
                db_optimizer_run = \
                    (await writer_reader.select(cls.RUN_SCHEDULE_TABLE, query.id == updated_queue[cls.CONFIG_ID]))[0]
                runs = updated_queue[cls.CONFIG_RUNS]
                to_remove_indexes = []
                # remove deleted runs and runs that are not in the queue anymore (already running or done)
                for run_index, run_data in enumerate(copy.copy(runs)):
                    if cls._contains_run(db_optimizer_run, run_data):
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

    async def run_single_iteration(self,
                                   optimizer_id,
                                   randomly_chose_runs=False,
                                   start_timestamp=None,
                                   end_timestamp=None):
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
            return await self._run_with_config(optimizer_id, data_files, backtesting_run_id, run_details,
                                               start_timestamp=start_timestamp, end_timestamp=end_timestamp)
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
                end_timestamp=end_timestamp
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
        run_db_manager = databases.DatabaseManager(self.trading_mode, self.optimization_campaign_name,
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

    def _generate_runs(self):
        iterations = [i for i in self._get_config_possible_iterations() if i]
        runs = {
            index: run
            for index, run in enumerate(itertools.product(*iterations))
            if self._is_run_allowed(run)
        }
        if runs:
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

        if operator == "lower_than":
            return left_operand < right_operand
        if operator == "higher_than":
            return left_operand > right_operand
        if operator == "lower_or_equal_to":
            return left_operand <= right_operand
        if operator == "higher_or_equal_to":
            return left_operand >= right_operand
        if operator == "equal_to":
            return left_operand == right_operand
        if operator == "different_from":
            return left_operand != right_operand
        raise RuntimeError(f"Unknown operator: {operator}")

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
            self.CONFIG_DATA_FILES: self.data_files,
            self.CONFIG_ID: self.optimizer_id
        }
        self.total_nb_runs = len(runs)
        async with databases.DBWriter.database(self.database_manager.get_optimizer_runs_schedule_identifier(),
                                               with_lock=True) as writer:
            await writer.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)
