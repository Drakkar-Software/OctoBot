#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import logging
import math
import copy

import octobot_commons.data_util as data_util
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.logging as common_logging
import octobot_commons.constants as commons_constants

import octobot.constants as constants
import octobot.strategy_optimizer as strategy_optimizer

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants

import octobot_evaluators.constants as evaluator_constants
import octobot_evaluators.evaluators as evaluators

import octobot_trading.modes as trading_modes

CONFIG = 0
RANK = 1
TRADES = 0
TRADES_IN_RESULT = 2


class StrategyOptimizer:
    """
    StrategyOptimizer is a tool that performs backtesting with different configurations
    """

    def __init__(self, config, tentacles_setup_config, strategy_name):
        # Lazy import of tentacles to let tentacles manager handle imports
        import tentacles.Evaluator as tentacles_Evaluator
        self.is_properly_initialized = False
        self.logger = common_logging.get_logger(self.get_name())
        self.config = config
        self.tentacles_setup_config = copy.deepcopy(tentacles_setup_config)
        self.trading_mode = trading_modes.get_activated_trading_mode(tentacles_setup_config)
        self.strategy_class = tentacles_management.get_class_from_string(
            strategy_name, evaluators.StrategyEvaluator,
            tentacles_Evaluator.Strategies, tentacles_management.evaluator_parent_inspection)
        self.run_results = []
        self.sorted_results_by_time_frame = {}
        self.sorted_results_through_all_time_frame = []
        self.all_time_frames = []
        self.all_TAs = []
        self.risks = []
        self.current_test_suite = None
        self.errors = set()

        self.is_computing = False
        self.is_finished = False
        self.run_id = 0
        self.total_nb_runs = 0

        self.keep_running = True

        if not self.strategy_class:
            self.logger.error(f"Impossible to find a strategy matching class name: {strategy_name} in installed "
                              f"strategies. Please make sure to enter the name of the class, "
                              f"ex: FullMixedStrategiesEvaluator")
        else:
            self.is_properly_initialized = True

    def find_optimal_configuration(self, TAs=None, time_frames=None, risks=None):
        if not self.is_computing:

            # set is_computing to True to prevent any simultaneous start
            self.is_computing = True

            self.errors = set()
            self.run_results = []
            self.sorted_results_by_time_frame = {}
            self.sorted_results_through_all_time_frame = []

            previous_log_level = common_logging.get_global_logger_level()

            try:
                self.all_TAs = self._get_all_TA() if TAs is None else TAs
                nb_TAs = len(self.all_TAs)

                self.all_time_frames = self.strategy_class.get_required_time_frames(self.config,
                                                                                    self.tentacles_setup_config) \
                    if time_frames is None else time_frames
                nb_TFs = len(self.all_time_frames)

                self.risks = [1] if risks is None else risks

                self.logger.info(f"Trying to find an optimized configuration for {self.strategy_class.get_name()} "
                                 f"strategy using {self.trading_mode.get_name()} trading mode, {self.all_TAs} "
                                 f"technical evaluator(s), {self.all_time_frames} time frames and {self.risks} "
                                 f"risk(s).")

                self.total_nb_runs = int(len(self.risks) * ((math.pow(2, nb_TFs) - 1) * (math.pow(2, nb_TAs) - 1)))

                self.logger.info("Setting logging level to logging.ERROR to limit messages.")
                common_logging.set_global_logger_level(logging.ERROR)

                self.run_id = 1
                self._iterate_on_configs(nb_TAs, nb_TFs)
                self._find_optimal_configuration_using_results()
            finally:
                self.current_test_suite = None
                common_logging.set_global_logger_level(previous_log_level)
                self.is_computing = False
                self.is_finished = True
                self.logger.info(f"{self.get_name()} finished computation.")
                self.logger.info("Logging level restored.")
        else:
            raise RuntimeError(f"{self.get_name()} is already computing: processed "
                               f"{self.run_id}/{self.total_nb_runs} processed")

    def _iterate_on_configs(self, nb_TAs, nb_TFs):
        # test with several risks
        for risk in self.risks:
            self.config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_RISK] = risk
            eval_conf_history = []
            # test with several evaluators
            for evaluator_conf_iteration in range(nb_TAs):
                current_forced_evaluator = self.all_TAs[evaluator_conf_iteration]
                # test with 1-n evaluators at a time
                for nb_evaluators in range(1, nb_TAs + 1):
                    # test different configurations
                    for _ in range(nb_TAs):
                        activated_evaluators = self._get_activated_element(self.all_TAs,
                                                                           current_forced_evaluator,
                                                                           nb_evaluators, eval_conf_history,
                                                                           self.strategy_class.get_name(),
                                                                           True)
                        if activated_evaluators is not None:
                            self._adapt_tentacles_config(activated_evaluators)
                            time_frames_conf_history = []
                            # test different time frames
                            for time_frame_conf_iteration in range(nb_TFs):
                                current_forced_time_frame = self.all_time_frames[time_frame_conf_iteration]
                                # test with 1-n time frames at a time
                                for nb_time_frames in range(1, nb_TFs + 1):
                                    # test different configurations
                                    for _ in range(nb_TFs):
                                        if not self.keep_running:
                                            return
                                        self._run_on_config(risk, current_forced_time_frame, nb_time_frames,
                                                            time_frames_conf_history, activated_evaluators)

    def _run_on_config(self, risk, current_forced_time_frame, nb_time_frames,
                       time_frames_conf_history, activated_evaluators):
        activated_time_frames = self._get_activated_element(self.all_time_frames,
                                                            current_forced_time_frame,
                                                            nb_time_frames,
                                                            time_frames_conf_history)
        if activated_time_frames is not None:
            self.config[evaluator_constants.CONFIG_FORCED_TIME_FRAME] = activated_time_frames
            print(f"{self.run_id}/{self.total_nb_runs} Run with: evaluators: {activated_evaluators}, "
                  f"time frames :{activated_time_frames}, risk: {risk}")
            self._run_test_suite(self.config, activated_evaluators)
            print(f" => Result: {self.run_results[-1].get_result_string(False)}")
            self.run_id += 1

    def _run_test_suite(self, config, evaluators):
        self.current_test_suite = strategy_optimizer.StrategyTestSuite()
        self.current_test_suite.evaluators = list(evaluators)
        self.current_test_suite.initialize_with_strategy(self.strategy_class,
                                                         self.tentacles_setup_config,
                                                         copy.deepcopy(config))
        no_error = asyncio.run(self.current_test_suite.run_test_suite(self.current_test_suite),
                               debug=constants.OPTIMIZER_FORCE_ASYNCIO_DEBUG_OPTION)
        if not no_error:
            self.errors = self.errors.union(set([str(e) for e in self.current_test_suite.exceptions]))
        run_result = self.current_test_suite.get_test_suite_result()
        self.run_results.append(run_result)

    def _adapt_tentacles_config(self, activated_evaluators):
        # Lazy import of tentacles to let tentacles manager handle imports
        import tentacles.Evaluator as tentacles_Evaluator
        to_update_config = {}
        tentacles_activation = tentacles_manager_api.get_tentacles_activation(self.tentacles_setup_config)
        for tentacle_class_name in tentacles_activation[tentacles_manager_constants.TENTACLES_EVALUATOR_PATH]:
            if tentacle_class_name in activated_evaluators:
                to_update_config[tentacle_class_name] = True
            elif tentacles_management.get_class_from_string(tentacle_class_name, evaluators.StrategyEvaluator,
                                                            tentacles_Evaluator.Strategies,
                                                            tentacles_management.evaluator_parent_inspection) is None:
                to_update_config[tentacle_class_name] = False
        tentacles_manager_api.update_activation_configuration(self.tentacles_setup_config, to_update_config, False)

    def _find_optimal_configuration_using_results(self):
        for time_frame in self.all_time_frames:
            time_frame_sorted_results = self._get_sorted_results(self.run_results, time_frame)
            self.sorted_results_by_time_frame[time_frame.value] = time_frame_sorted_results

        results_through_all_time_frame = {}
        for results in self.sorted_results_by_time_frame.values():
            for rank, result in enumerate(results):
                result_summary = result.get_config_summary()
                if result_summary not in results_through_all_time_frame:
                    results_through_all_time_frame[result_summary] = [[], 0]
                results_through_all_time_frame[result_summary][RANK] += rank
                results_through_all_time_frame[result_summary][TRADES] += result.trades_counts

        result_list = [(result, trades_and_rank[RANK], data_util.mean(trades_and_rank[TRADES]))
                       for result, trades_and_rank in results_through_all_time_frame.items()]

        # inner function to replace uncythonizable lambda expression
        def _sorting_key(elem):
            return elem[RANK]

        self.sorted_results_through_all_time_frame = sorted(result_list, key=_sorting_key)

    def print_report(self):
        self.logger.info("Full execution sorted results: Minimum time frames are defining the range of the run "
                         "since it finishes at the end of the first data, aka minimum time frame. Therefore all "
                         "different time frames are different price actions and can't be compared independently.")
        for time_frame, results in self.sorted_results_by_time_frame.items():
            self.logger.info(f" *** {time_frame} minimum time frame ranking*** ")
            for rank, result in enumerate(results):
                self.logger.info(f"{rank}: {result.get_result_string()}")
        self.logger.info(f" *** Top rankings per time frame *** ")
        for time_frame, results in self.sorted_results_by_time_frame.items():
            for i in range(0, min(len(results), 5)):
                self.logger.info(f"{time_frame}: {results[i].get_result_string(False)}")
        self.logger.info(f" *** Top rankings through all time frames *** ")
        for rank, result in enumerate(self.sorted_results_through_all_time_frame[0:25]):
            self.logger.info(f"{rank}: {result[CONFIG].get_result_string()} (time frame rank sum: {result[RANK]}) "
                             f"average trades count: {result[TRADES_IN_RESULT]:f}")
        self.logger.info(f" *** Overall best configuration for {self.strategy_class.get_name()} using "
                         f"{self.trading_mode.get_name()} trading mode *** ")
        best_result = self.sorted_results_through_all_time_frame[0]
        self.logger.info(f"{best_result[CONFIG].get_result_string()} "
                         f"average trades count: {best_result[TRADES_IN_RESULT]:f}")

    async def get_overall_progress(self):
        return int((self.run_id - 1) / self.total_nb_runs * 100) if self.total_nb_runs else 0, 0

    async def is_in_progress(self):
        return self.get_overall_progress() != 100

    def cancel(self):
        self.keep_running = False

    def get_current_test_suite_progress(self):
        return self.current_test_suite.current_progress if self.current_test_suite else 0

    def get_report(self):
        # index, evaluators, risk, score, trades
        if self.sorted_results_through_all_time_frame:
            results = [strategy_optimizer.TestSuiteResult.convert_result_into_dict(rank, result[CONFIG].evaluators, "",
                                                                                   result[CONFIG].risk, result[RANK],
                                                                                   round(result[TRADES_IN_RESULT], 5))
                       for rank, result in enumerate(self.sorted_results_through_all_time_frame[0:100])]
        else:
            results = []
        return results

    def get_errors_description(self):
        if self.errors:
            return f"{', '.join(self.errors)[0:350]} ..."
        else:
            return None

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    def _get_activated_element(all_elements, current_forced_element, nb_elements_to_consider,
                               elem_conf_history, default_element=None, dict_shaped=False):
        eval_conf = {current_forced_element: True}
        additional_elements_count = 0
        if default_element is not None:
            eval_conf[default_element] = True
            additional_elements_count = 1
        if nb_elements_to_consider > 1:
            i = 0
            while i < len(all_elements) and \
                    len(eval_conf) < nb_elements_to_consider + additional_elements_count:
                current_elem = all_elements[i]
                if current_elem not in eval_conf:
                    eval_conf[current_elem] = True
                    if len(eval_conf) == nb_elements_to_consider + additional_elements_count and \
                            ((eval_conf if dict_shaped else sorted([key.value for key in eval_conf]))
                             in elem_conf_history):
                        eval_conf.pop(current_elem)
                i += 1
        if len(eval_conf) == nb_elements_to_consider + additional_elements_count:
            to_use_conf = eval_conf
            if not dict_shaped:
                to_use_conf = sorted([key.value for key in eval_conf])
            if to_use_conf not in elem_conf_history:
                elem_conf_history.append(to_use_conf)
                return to_use_conf
        return None

    @staticmethod
    def _get_filtered_results(results, time_frame=None):
        return [result for result in results if time_frame is None or result.min_time_frame == time_frame]

    @staticmethod
    def _get_sorted_results(results, time_frame=None):
        return sorted(StrategyOptimizer._get_filtered_results(results, time_frame),
                      key=lambda result: result.get_average_score(), reverse=True)

    @staticmethod
    def _is_relevant_evaluation_config(evaluator):
        # Lazy import of tentacles to let tentacles manager handle imports
        import tentacles.Evaluator as tentacles_Evaluator
        return tentacles_management.get_class_from_string(
            evaluator, evaluators.TAEvaluator, tentacles_Evaluator.TA,
            tentacles_management.evaluator_parent_inspection) is not None

    def _get_all_TA(self):
        return [evaluator
                for evaluator, activated
                in tentacles_manager_api.get_tentacles_activation(self.tentacles_setup_config)[
                    tentacles_manager_constants.TENTACLES_EVALUATOR_PATH].items()
                if activated and StrategyOptimizer._is_relevant_evaluation_config(evaluator)]
