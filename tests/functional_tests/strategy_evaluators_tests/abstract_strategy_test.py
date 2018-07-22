from abc import ABCMeta, abstractmethod

from tests.test_utils.backtesting_util import create_backtesting_config, create_backtesting_bot, \
    start_backtesting_bot, filter_wanted_symbols
from config.cst import CONFIG_EVALUATOR
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection


DEFAULT_SYMBOL = "ICX/BTC"


class AbstractStrategyTest:
    __metaclass__ = ABCMeta

    def init(self, strategy_evaluator_class):
        self.config = create_backtesting_config(filter_symbols=False)
        self.strategy_evaluator_class = strategy_evaluator_class
        self._register_only_strategy(strategy_evaluator_class)
        self._assert_init()

    # plays a backtesting with this strategy market profitability: tf[30m]: -13.325377883850436
    @staticmethod
    @abstractmethod
    def test_default_run(strategy_tester):
        raise NotImplementedError("test_default_run not implemented")

    def run_test_default_run(self, profitability):
        run_results = self._run_backtesting_with_current_config(DEFAULT_SYMBOL)
        self._assert_results(run_results, profitability)

    @staticmethod
    def _assert_results(run_results, profitability):
        assert run_results[0] >= profitability

    def _run_backtesting_with_current_config(self, symbol):
        filter_wanted_symbols(self.config, [symbol])
        bot = create_backtesting_bot(self.config)
        return start_backtesting_bot(bot)

    def _register_only_strategy(self, strategy_evaluator_class):
        for evaluatotor_name in self.config[CONFIG_EVALUATOR]:
            if get_class_from_string(evaluatotor_name, StrategiesEvaluator, Strategies,
                                     evaluator_parent_inspection) is not None:
                self.config[CONFIG_EVALUATOR][evaluatotor_name] = False
        self.config[CONFIG_EVALUATOR][strategy_evaluator_class.get_name()] = True

    def _assert_init(self):
        assert self.config
        assert self.config[CONFIG_EVALUATOR][self.strategy_evaluator_class.get_name()] is True
