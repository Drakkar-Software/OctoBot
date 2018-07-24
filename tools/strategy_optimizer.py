import logging
import copy

from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from tests.test_utils.backtesting_util import add_config_default_backtesting_values
from tests.test_utils.config import load_test_config
from evaluator.TA.TA_evaluator import TAEvaluator
from evaluator import TA
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test import AbstractStrategyTest
from config.cst import CONFIG_TRADER_RISK, CONFIG_TRADER, CONFIG_FORCED_EVALUATOR, CONFIG_FORCED_TIME_FRAME, \
    CONFIG_EVALUATOR, CONFIG_CATEGORY_SERVICES, CONFIG_WEB, CONFIG_ENABLED_OPTION, CONFIG_TRADER_MODE

PROFITABILITY = "profitability"
BOT_PROFITABILITY = 0
MARKET_PROFITABILITY = 1
CONFIGURATION = "configuration"
RESULT = "result"
ACTIVATED_EVALUATORS = "activated_evaluators"


class StrategyOptimizer:

    def __init__(self, config, strategy_name):
        self.is_properly_initialized = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = load_test_config()
        self.config[CONFIG_TRADER][CONFIG_TRADER_MODE] = config[CONFIG_TRADER][CONFIG_TRADER_MODE]
        self.config[CONFIG_EVALUATOR] = config[CONFIG_EVALUATOR]
        add_config_default_backtesting_values(self.config)
        self.strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                                    Strategies, evaluator_parent_inspection)
        self.run_results = []
        self.optimal_configuration = {}

        if not self.strategy_class:
            self.logger.error(f"Impossible to find a strategy matching class name: {strategy_name} in installed "
                              f"strategies. Please make sure to enter the name of the class, "
                              f"ex: FullMixedStrategiesEvaluator")
        else:
            self.is_properly_initialized = True

    def find_optimal_configuration(self):
        self.logger.info(f"Trying to find an optmized configuration for {self.strategy_class.get_name()} strategy")
        self.logger.setLevel(logging.ERROR)

        all_TAs = self._get_all_TA(self.config[CONFIG_EVALUATOR])
        nb_TAs = len(all_TAs)

        all_time_frames = self.strategy_class.get_required_time_frames(self.config)
        nb_TFs = len(all_time_frames)

        # test with several risks
        for risk in [i/2 for i in range(1, 3)]:
            self.config[CONFIG_TRADER][CONFIG_TRADER_RISK] = risk
            eval_conf_history = []
            # test with several evaluators
            for evaluator_conf_iteration in range(nb_TAs):
                current_forced_evaluator = all_TAs[evaluator_conf_iteration]
                # test with 1-n evaluators at a time
                for nb_evaluators in range(1, nb_TAs+1):
                    # test different configurations
                    for i in range(nb_TAs):
                        activated_evaluators = self.get_activated_evaluators(all_TAs, current_forced_evaluator,
                                                                             nb_evaluators, eval_conf_history,
                                                                             self.strategy_class.get_name(), True)
                        if activated_evaluators is not None:
                            self.config[CONFIG_FORCED_EVALUATOR] = activated_evaluators
                            time_frames_conf_history = []
                            # test different time frames
                            for time_frame_conf_iteration in range(nb_TFs):
                                current_forced_time_frame = all_time_frames[time_frame_conf_iteration]
                                # test with 1-n time frames at a time
                                for nb_time_frames in range(1, nb_TFs+1):
                                    # test different configurations
                                    for j in range(nb_TFs):
                                        activated_time_frames = \
                                            self.get_activated_evaluators(all_time_frames, current_forced_time_frame,
                                                                          nb_time_frames, time_frames_conf_history)
                                        if activated_time_frames is not None:
                                            self.config[CONFIG_FORCED_TIME_FRAME] = activated_time_frames
                                            print(f"Run with: evaluators: {activated_evaluators}, time frames :"
                                                  f"{activated_time_frames}, risk: {risk}")
                                            self._run_test_suite(self.config)

        self._find_optimal_configuration_using_results()

    def get_activated_evaluators(self, all_elements, current_forced_element, nb_elements_to_consider,
                                 elem_conf_history, default_element=None, dict_shaped=False):
        eval_conf = {current_forced_element: True}
        additional_elements_count = 0
        if default_element is not None:
            eval_conf[default_element] = True
            additional_elements_count = 1
        if nb_elements_to_consider > 1:
            i = 0
            while i < len(all_elements) and \
                    len(eval_conf) < nb_elements_to_consider+additional_elements_count:
                current_elem = all_elements[i]
                if current_elem not in eval_conf:
                    eval_conf[current_elem] = True
                    if len(eval_conf) == nb_elements_to_consider+additional_elements_count and \
                            ((eval_conf if dict_shaped else sorted([key.value for key in eval_conf])) in elem_conf_history):
                        eval_conf.pop(current_elem)
                i += 1
        if len(eval_conf) == nb_elements_to_consider+additional_elements_count:
            to_use_conf = eval_conf
            if not dict_shaped:
                to_use_conf = sorted([key.value for key in eval_conf])
            if to_use_conf not in elem_conf_history:
                elem_conf_history.append(to_use_conf)
                return to_use_conf
        return None

    def _run_test_suite(self, config):
        strategy_test_suite = StrategyOptimizer.StrategyTestSuite()
        strategy_test_suite.init(self.strategy_class, copy.deepcopy(config))
        strategy_test_suite.run_test_suite(strategy_test_suite)
        run_result = {
            CONFIGURATION: config,
            PROFITABILITY: strategy_test_suite.profitability_results
        }
        self.run_results.append(run_result)

    def get_best_run_config(self):
        return sorted(self.run_results, key=lambda result: self.get_average_score(result))[0]

    @staticmethod
    def get_average_score(result):
        bot_profitabilities = [profitability_result[BOT_PROFITABILITY] - profitability_result[MARKET_PROFITABILITY]
                               for profitability_result in result[PROFITABILITY]]
        return sum(bot_profitabilities) / len(bot_profitabilities)


    def _find_optimal_configuration_using_results(self):
        optimal_config = self.get_best_run_config()
        self.optimal_configuration[ACTIVATED_EVALUATORS] = self._get_all_TA(optimal_config[CONFIG_FORCED_EVALUATOR])
        self.optimal_configuration[CONFIG_EVALUATOR] = optimal_config[CONFIG_FORCED_TIME_FRAME]
        self.optimal_configuration[CONFIG_TRADER_RISK] = optimal_config[CONFIG_TRADER][CONFIG_TRADER_RISK]

    @staticmethod
    def _get_all_TA(config_evaluator):
        return [evaluator
                for evaluator, activated in config_evaluator.items()
                if activated and StrategyOptimizer._is_relevant_evaluation_config(evaluator)]

    @staticmethod
    def _is_relevant_evaluation_config(evaluator):
        return get_class_from_string(evaluator, TAEvaluator, TA, evaluator_parent_inspection) is not None

    def print_report(self):
        self.logger.setLevel(logging.INFO)
        self.logger.info(f"{self.strategy_class} best configuration is: {self.optimal_configuration}")

    class StrategyTestSuite(AbstractStrategyTest):

        def __init__(self):
            super().__init__()
            self.profitability_results = []

        def run_test_suite(self, strategy_tester):
            self.test_slow_downtrend(strategy_tester)
            print('.',)
            self.test_sharp_downtrend(strategy_tester)
            print('.',)
            self.test_flat_markets(strategy_tester)
            print('.',)
            self.test_slow_uptrend(strategy_tester)
            print('.',)
            self.test_sharp_uptrend(strategy_tester)
            print('.',)


        @staticmethod
        def test_default_run(strategy_tester):
            strategy_tester.run_test_default_run(None)

        @staticmethod
        def test_slow_downtrend(strategy_tester):
            strategy_tester.run_test_slow_downtrend(None, None, None)

        @staticmethod
        def test_sharp_downtrend(strategy_tester):
            strategy_tester.run_test_sharp_downtrend(None)

        @staticmethod
        def test_flat_markets(strategy_tester):
            strategy_tester.run_test_flat_markets(None, None, None)

        @staticmethod
        def test_slow_uptrend(strategy_tester):
            strategy_tester.run_test_slow_uptrend(None, None)

        @staticmethod
        def test_sharp_uptrend(strategy_tester):
            strategy_tester.run_test_sharp_uptrend(None, None)

        def _assert_results(self, run_results, profitability):
            self.profitability_results.append(run_results)
