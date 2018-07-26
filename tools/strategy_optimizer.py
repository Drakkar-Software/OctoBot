import logging
import copy
import math

from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from tools.time_frame_manager import TimeFrameManager
from tests.test_utils.backtesting_util import add_config_default_backtesting_values
from tests.test_utils.config import load_test_config
from evaluator.TA.TA_evaluator import TAEvaluator
from evaluator import TA
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test import AbstractStrategyTest
from config.cst import CONFIG_TRADER_RISK, CONFIG_TRADER, CONFIG_FORCED_EVALUATOR, CONFIG_FORCED_TIME_FRAME, \
    CONFIG_EVALUATOR, CONFIG_TRADER_MODE
from trading.exchanges.exchange_simulator.exchange_simulator import NoCandleDataForThisTimeFrameException

BOT_PROFITABILITY = 0
MARKET_PROFITABILITY = 1
CONFIG = 0
RANK = 1


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
        self.results_report = []
        self.sorted_results_by_time_frame = {}
        self.sorted_results_through_all_time_frame = {}
        self.all_time_frames = []

        if not self.strategy_class:
            self.logger.error(f"Impossible to find a strategy matching class name: {strategy_name} in installed "
                              f"strategies. Please make sure to enter the name of the class, "
                              f"ex: FullMixedStrategiesEvaluator")
        else:
            self.is_properly_initialized = True

    def find_optimal_configuration(self):
        self.logger.info(f"Trying to find an optmized configuration for {self.strategy_class.get_name()} strategy")

        all_TAs = self.get_all_TA(self.config[CONFIG_EVALUATOR])
        nb_TAs = len(all_TAs)

        self.all_time_frames = self.strategy_class.get_required_time_frames(self.config)
        nb_TFs = len(self.all_time_frames)

        risks = [0.5, 1]

        nb_runs = int(len(risks) * (math.pow(nb_TFs, 2) * math.pow(nb_TAs, 2)))

        self.logger.setLevel(logging.ERROR)
        for handler in self.logger.parent.handlers:
            handler.setLevel(logging.ERROR)

        run_id = 1
        # test with several risks
        for risk in risks:
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
                                current_forced_time_frame = self.all_time_frames[time_frame_conf_iteration]
                                # test with 1-n time frames at a time
                                for nb_time_frames in range(1, nb_TFs+1):
                                    # test different configurations
                                    for j in range(nb_TFs):
                                        activated_time_frames = \
                                            self.get_activated_evaluators(self.all_time_frames,
                                                                          current_forced_time_frame,
                                                                          nb_time_frames, time_frames_conf_history)
                                        if activated_time_frames is not None:
                                            self.config[CONFIG_FORCED_TIME_FRAME] = activated_time_frames
                                            print(f"{run_id}/{nb_runs} Run with: evaluators: {activated_evaluators}, "
                                                  f"time frames :{activated_time_frames}, risk: {risk}")
                                            self._run_test_suite(self.config)
                                            print(f" => Result: {self.run_results[-1].get_result_string(False)}")
                                            run_id += 1

        self.logger.setLevel(logging.INFO)
        for handler in self.logger.parent.handlers:
            handler.setLevel(logging.INFO)
        self._find_optimal_configuration_using_results()

    @staticmethod
    def get_activated_evaluators(all_elements, current_forced_element, nb_elements_to_consider,
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
                            ((eval_conf if dict_shaped else sorted([key.value for key in eval_conf]))
                             in elem_conf_history):
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
        run_result = strategy_test_suite.get_test_suite_result()
        self.run_results.append(run_result)

    @staticmethod
    def get_filtered_results(results, time_frame=None):
        return [result for result in results if time_frame is None or result.min_time_frame == time_frame]

    @staticmethod
    def get_sorted_results(results, time_frame=None):
        return sorted(StrategyOptimizer.get_filtered_results(results, time_frame),
                      key=lambda result: result.get_average_score(), reverse=True)

    def _find_optimal_configuration_using_results(self):
        for time_frame in self.all_time_frames:
            time_frame_sorted_results = self.get_sorted_results(self.run_results, time_frame)
            self.sorted_results_by_time_frame[time_frame.value] = time_frame_sorted_results

        results_through_all_time_frame = {}
        for results in self.sorted_results_by_time_frame.values():
            for rank, result in enumerate(results):
                result_summary = result.get_config_summary()
                if result_summary not in results_through_all_time_frame:
                    results_through_all_time_frame[result_summary] = 0
                results_through_all_time_frame[result_summary] += rank
        result_list = [(result, rank) for result, rank in results_through_all_time_frame.items()]
        self.sorted_results_through_all_time_frame = sorted(result_list, key=lambda res: res[RANK])

    @staticmethod
    def _is_relevant_evaluation_config(evaluator):
        return get_class_from_string(evaluator, TAEvaluator, TA, evaluator_parent_inspection) is not None

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
            self.logger.info(f"{rank}: {result[CONFIG].get_result_string()} (time frame rank sum: {result[RANK]})")
        self.logger.info(f" *** Overall best configuration for {self.strategy_class.get_name()}*** ")
        self.logger.info(f"{self.sorted_results_through_all_time_frame[0][CONFIG].get_result_string()}")

    @staticmethod
    def get_all_TA(config_evaluator):
        return [evaluator
                for evaluator, activated in config_evaluator.items()
                if activated and StrategyOptimizer._is_relevant_evaluation_config(evaluator)]

    class TestSuiteResult:
        def __init__(self, run_profitabilities, trades_counts, risk, time_frames, evaluators, strategy):
            self.run_profitabilities = run_profitabilities
            self.trades_counts = trades_counts
            self.risk = risk
            self.time_frames = time_frames
            self.min_time_frame = TimeFrameManager.find_min_time_frame(self.time_frames)
            self.evaluators = evaluators
            self.strategy = strategy

        def get_average_score(self):
            bot_profitabilities = [
                profitability_result[BOT_PROFITABILITY] - profitability_result[MARKET_PROFITABILITY]
                for profitability_result in self.run_profitabilities]
            return sum(bot_profitabilities) / len(bot_profitabilities) if bot_profitabilities else 0

        def get_average_trades_count(self):
            return sum(self.trades_counts) / len(self.trades_counts) if self.trades_counts else 0

        def get_evaluators_without_strategy(self):
            evals = copy.copy(self.evaluators)
            evals.pop(self.strategy)
            return [eval_name for eval_name in evals]

        def get_config_summary(self):
            return StrategyOptimizer.TestSuiteResultSummary(self)

        def get_result_string(self, details=True):
            details = f" details: (profitabilities (bot, market):{self.run_profitabilities}, trades: " \
                      f"{self.trades_counts})" if details else ""
            return (f"{self.get_evaluators_without_strategy()} on {self.time_frames} at risk: {self.risk} "
                    f"score: {self.get_average_score():f} (the higher the better) "
                    f"average trades: {self.get_average_trades_count():f}{details}")

    class TestSuiteResultSummary:
        def __init__(self, test_suite_result):
            self.evaluators = test_suite_result.get_evaluators_without_strategy()
            self.risk = test_suite_result.risk

        def get_result_string(self):
            return f"{self.evaluators} risk: {self.risk}"

        def __eq__(self, other):
            return self.evaluators == other.evaluators and self.risk == other.risk

        def __hash__(self):
            return abs(hash(f"{self.evaluators}{self.risk}"))

    class StrategyTestSuite(AbstractStrategyTest):

        SKIP_LONG_STEPS = False

        def __init__(self):
            super().__init__()
            self._profitability_results = []
            self._trades_counts = []
            self.logger = logging.getLogger(self.__class__.__name__)

        def get_test_suite_result(self):
            return StrategyOptimizer.TestSuiteResult(self._profitability_results,
                                                     self._trades_counts,
                                                     self.config[CONFIG_TRADER][CONFIG_TRADER_RISK],
                                                     self.config[CONFIG_FORCED_TIME_FRAME],
                                                     self.config[CONFIG_FORCED_EVALUATOR],
                                                     self.strategy_evaluator_class.get_name())

        def run_test_suite(self, strategy_tester):
            tests = [self.test_slow_downtrend, self.test_sharp_downtrend, self.test_flat_markets,
                     self.test_slow_uptrend, self.test_sharp_uptrend]
            print('| ', end='')
            for test in tests:
                try:
                    test(strategy_tester)
                except NoCandleDataForThisTimeFrameException:
                    pass
                except Exception as e:
                    print(f"Exception when running test {test.__name__}: {e}")
                    self.logger.exception(e)
                print('#', end='')
            print(' |', end='')

        @staticmethod
        def test_default_run(strategy_tester):
            strategy_tester.run_test_default_run(None)

        @staticmethod
        def test_slow_downtrend(strategy_tester):
            strategy_tester.run_test_slow_downtrend(None, None, None,
                                                    StrategyOptimizer.StrategyTestSuite.SKIP_LONG_STEPS)

        @staticmethod
        def test_sharp_downtrend(strategy_tester):
            strategy_tester.run_test_sharp_downtrend(None)

        @staticmethod
        def test_flat_markets(strategy_tester):
            strategy_tester.run_test_flat_markets(None, None, None,
                                                  StrategyOptimizer.StrategyTestSuite.SKIP_LONG_STEPS)

        @staticmethod
        def test_slow_uptrend(strategy_tester):
            strategy_tester.run_test_slow_uptrend(None, None)

        @staticmethod
        def test_sharp_uptrend(strategy_tester):
            strategy_tester.run_test_sharp_uptrend(None, None)

        def _assert_results(self, run_results, profitability, bot):
            self._profitability_results.append(run_results)
            trader = next(iter(bot.get_exchange_trader_simulators().values()))
            self._trades_counts.append(len(trader.get_trades_manager().get_trade_history()))
