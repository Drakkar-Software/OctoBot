import logging
import copy

from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from evaluator.TA.TA_evaluator import TAEvaluator
from evaluator import TA
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test import AbstractStrategyTest
from config.cst import CONFIG_TRADER_RISK, CONFIG_TRADER, CONFIG_EVALUATOR

PROFITABILITY = "profitability"
MARKET_PROFITABILITY = "market_profitability"
CONFIGURATION = "configuration"
RESULT = "result"
ACTIVATED_EVALUATORS = "activated_evaluators"
ACTIVATED_TIME_FRAMES = "activated_time_frames"


class StrategyOptimizer:

    def __init__(self, config, strategy_name):
        self.is_properly_initialized = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                                    Strategies, evaluator_parent_inspection)
        self.run_results = {}
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
        self._find_optimal_configuration_using_results()

    def _run_test_suite(self, config):
        strategy_test_suite = StrategyOptimizer.StrategyTestSuite()
        strategy_test_suite.init(self.strategy_class, copy.deepcopy(config))
        self.run_results[config] = strategy_test_suite.profitability_results

    def _find_optimal_configuration_using_results(self):
        optimal_config = self.config
        self.optimal_configuration[ACTIVATED_EVALUATORS] = [evaluator.get_name()
                                                            for evaluator, activated
                                                            in optimal_config[CONFIG_EVALUATOR].items()
                                                            if activated and
                                                            self._is_relevant_evaluation_config(evaluator)]
        self.optimal_configuration[ACTIVATED_TIME_FRAMES] = []
        self.optimal_configuration[CONFIG_TRADER_RISK] = optimal_config[CONFIG_TRADER][CONFIG_TRADER_RISK]

    @staticmethod
    def _is_relevant_evaluation_config(evaluator):
        return get_class_from_string(evaluator, TAEvaluator, TA, evaluator_parent_inspection) is not None

    def print_report(self):
        print(self.strategy_class.get_name())

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
            self.profitability_results.append({
                PROFITABILITY: run_results[0],
                MARKET_PROFITABILITY: run_results[1]
            })
