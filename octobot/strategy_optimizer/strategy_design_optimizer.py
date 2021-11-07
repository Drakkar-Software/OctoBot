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
import os
import itertools
import enum
import random
import copy

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.tentacles_management as tentacles_management
import octobot.constants as constants
import octobot_trading.modes.scripting_library as scripting_library
import octobot_trading.modes as trading_modes
import octobot.api.backtesting as octobot_backtesting_api
import octobot_backtesting.errors as backtesting_errors
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_evaluators.evaluators as evaluators


class ConfigTypes(enum.Enum):
    NUMBER = "number"
    BOOLEAN = "boolean"
    OPTIONS = "options"
    UNKNOWN = "unknown"


class NoMoreRunError(Exception):
    pass


class StrategyDesignOptimizer:
    MAX_OPTIMIZER_RUNS = 100000
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

        self.is_computing = False
        self.current_run_id = 0
        self.total_nb_runs = 0
        self.keep_running = True

    async def initialize(self):
        self.optimizer_id = self._get_new_optimizer_id()
        await self._store_backtesting_runs_schedule()

    def get_name(self) -> str:
        return f"{self.trading_mode.get_name()}_{self.__class__.__name__}"

    async def find_optimal_configuration(self, randomly_chose_runs=False):
        try:
            self.is_computing = True
            self.current_run_id = 1
            self.total_nb_runs = None
            while self.keep_running:
                await self.run_single_iteration(randomly_chose_runs=randomly_chose_runs)
                self.current_run_id += 1
        except NoMoreRunError:
            async with scripting_library.DBWriter.database(self._get_run_schedule_db()) as writer:
                query = await writer.search()
                await writer.delete(self.RUN_SCHEDULE_TABLE, query.id == self.optimizer_id)
        finally:
            self.is_computing = False

    def cancel(self):
        self.keep_running = False

    def get_overall_progress(self):
        return int((self.current_run_id - 1) / self.total_nb_runs * 100) if self.total_nb_runs else 0

    def is_in_progress(self):
        return self.get_overall_progress() != 100

    def get_current_test_suite_progress(self):
        return 0

    def get_errors_description(self):
        return ""

    async def run_single_iteration(self, randomly_chose_runs=False):
        data_files = run_data = run_id = run_details = None
        async with scripting_library.DBReader.database(self._get_run_schedule_db()) as reader:
            if self.optimizer_id is None:
                raise RuntimeError("No optimizer id")
            self._update_config_for_optimizer()
            query = await reader.search()
            run_data = await reader.select(self.RUN_SCHEDULE_TABLE, query.id == self.optimizer_id)
            if run_data and run_data[0][self.CONFIG_RUNS]:
                runs = run_data[0][self.CONFIG_RUNS]
                data_files = run_data[0][self.CONFIG_DATA_FILES]
                run_ids = list(runs)
                run_count = len(run_ids)
                if self.total_nb_runs is None:
                    self.total_nb_runs = run_count
                run_id = random.randrange(run_count) if randomly_chose_runs else run_ids[0]
                run_details = runs.pop(run_id)
        if data_files:
            async with scripting_library.DBWriter.database(self._get_run_schedule_db()) as writer:
                query = await writer.search()
                updated_data = {
                    self.CONFIG_RUNS: run_data[0][self.CONFIG_RUNS]
                }
                await writer.update(self.RUN_SCHEDULE_TABLE, updated_data, query.id == self.optimizer_id)
            return await self._run_with_config(data_files, run_id, run_details)
        raise NoMoreRunError("Nothing to run")

    async def _run_with_config(self, data_files, run_id, run_config):
        self.logger.debug(f"Running optimizer with id {self.optimizer_id} "
                          f"on backtesting {run_id} with config {run_config}")
        tentacles_setup_config = self._get_custom_tentacles_setup_config(run_id, run_config)
        independent_backtesting = None
        try:
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

    def _update_config_for_optimizer(self):
        self.config[commons_constants.CONFIG_OPTIMIZER_ID] = self.optimizer_id

    def _get_custom_tentacles_setup_config(self, run_id, run_config):
        local_tentacles_setup_config = copy.deepcopy(self.base_tentacles_setup_config)
        run_folder = self._get_optimizer_run_folder(self.optimizer_id, run_id)
        tentacles_setup_config_path = os.path.join(run_folder, commons_constants.CONFIG_TENTACLES_FILE)
        tentacles_manager_api.set_tentacles_setup_configuration_path(local_tentacles_setup_config,
                                                                     tentacles_setup_config_path)
        tentacles_updates = {}
        for input_config in run_config:
            if input_config[self.CONFIG_TENTACLE] not in tentacles_updates:
                tentacles_updates[input_config[self.CONFIG_TENTACLE]] = {}
            tentacles_updates[input_config[self.CONFIG_TENTACLE]][input_config[self.CONFIG_USER_INPUT]] = \
                input_config[self.CONFIG_VALUE]
        self._ensure_local_config_folders(run_folder)
        for tentacle, updated_values in tentacles_updates.items():
            tentacle_class = self._find_tentacle_class(tentacle)
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

    @staticmethod
    def _find_tentacle_class(tentacle):
        # Lazy import of tentacles to let tentacles manager handle imports
        import tentacles.Trading as tentacles_trading
        tentacle_class = tentacles_management.get_class_from_string(
            tentacle, trading_modes.AbstractTradingMode,
            tentacles_trading.Mode, tentacles_management.trading_mode_parent_inspection)
        if tentacle_class:
            return tentacle_class
        import tentacles.Evaluator as tentacles_Evaluator
        tentacle_class = tentacles_management.get_class_from_string(
            tentacle, evaluators.StrategyEvaluator,
            tentacles_Evaluator.Strategies, tentacles_management.evaluator_parent_inspection)
        if tentacle_class:
            return tentacle_class
        tentacle_class = tentacles_management.get_class_from_string(
            tentacle, evaluators.TAEvaluator,
            tentacles_Evaluator.TA, tentacles_management.evaluator_parent_inspection)
        if tentacle_class:
            return tentacle_class
        raise RuntimeError(f"Can't fine tentacle: {tentacle}")

    async def _store_backtesting_runs_schedule(self):
        runs = self._generate_runs()
        await self._save_run_schedule(runs)

    def _generate_runs(self):
        iterations = [i for i in self._get_config_possible_iterations() if i]
        return {index: run for index, run in enumerate(itertools.product(*iterations))}

    def _get_config_possible_iterations(self):
        return [
            self._generate_possible_values(config_element)
            for config_element in self._get_config_elements()
        ]

    def _generate_possible_values(self, config_element):
        if not config_element:
            return {}
        values = []
        if config_element[self.CONFIG_ENABLED]:
            if config_element[self.CONFIG_TYPE] in (ConfigTypes.OPTIONS, ConfigTypes.BOOLEAN):
                values = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
            if config_element[self.CONFIG_TYPE] is ConfigTypes.NUMBER:
                config = config_element[self.CONFIG_VALUE][self.CONFIG_VALUE]
                values = range(config[self.CONFIG_MIN], config[self.CONFIG_MAX], config[self.CONFIG_STEP])
        return [
            {
                self.CONFIG_USER_INPUT: config_element[self.CONFIG_KEY],
                self.CONFIG_TENTACLE: config_element[self.CONFIG_VALUE][self.CONFIG_TENTACLE],
                self.CONFIG_VALUE: value
            }
            for value in values
        ]

    def _get_config_elements(self):
        for key, val in self.optimizer_config.items():
            yield {
                self.CONFIG_KEY: key,
                self.CONFIG_ENABLED: val[self.CONFIG_ENABLED],
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
        async with scripting_library.DBWriter.database(self._get_run_schedule_db()) as writer:
            await writer.log(self.RUN_SCHEDULE_TABLE, self.runs_schedule)

    def _get_run_schedule_db(self):
        return os.path.join(self._get_optimizer_run_folder(), constants.OPTIMIZER_RUNS_SCHEDULE_DB)

    def _get_optimizer_run_folder(self, optimizer_id=None, backtesting_run_id=None):
        folder = os.path.join(commons_constants.USER_FOLDER, self.trading_mode.get_name(),
                              commons_constants.OPTIMIZER_RUNS_FOLDER)
        if optimizer_id is not None:
            folder = os.path.join(folder, str(optimizer_id))
        if backtesting_run_id is not None:
            folder = os.path.join(folder, str(backtesting_run_id))
        return folder

    def _get_new_optimizer_id(self):
        index = 1
        name_candidate = self._get_optimizer_run_folder(index)
        while index < self.MAX_OPTIMIZER_RUNS:
            if os.path.exists(name_candidate):
                index += 1
                name_candidate = self._get_optimizer_run_folder(index)
            else:
                os.makedirs(name_candidate)
                return index
        raise RuntimeError(f"Can't find any optimizer run id")
