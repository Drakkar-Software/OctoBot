from abc import ABCMeta, abstractmethod
import copy

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

    # plays a backtesting with this strategy market profitability: tf[30m]: -13.325377883850436 %
    @staticmethod
    @abstractmethod
    def test_default_run(strategy_tester):
        raise NotImplementedError("test_default_run not implemented")

    # plays a backtesting with this strategy on a slow downtrend market: ICX/BTC[30m]: -13.325377883850436 %
    @staticmethod
    @abstractmethod
    def test_slow_downtrend(strategy_tester):
        raise NotImplementedError("test_slow_downtrend not implemented")

    # plays a backtesting with this strategy on a sharp downtrend market: VEN/BTC[30m] -20.281292481438868 %
    @staticmethod
    @abstractmethod
    def test_sharp_downtrend(strategy_tester):
        raise NotImplementedError("test_sharp_downtrend not implemented")

    # plays a backtesting with this strategy flat markets profitability:
    # 1. NEO/BTC[30m] -11.246861924686186 %
    # 2. XRB/BTC[30m] -5.834160873882809 %
    @staticmethod
    @abstractmethod
    def test_flat_markets(strategy_tester):
        raise NotImplementedError("test_flat_markets not implemented")

    # plays a backtesting with this strategy on a slow uptrend market: BTC/USDT[30m]: 0 (vs btc) %
    @staticmethod
    @abstractmethod
    def test_slow_uptrend(strategy_tester):
        raise NotImplementedError("test_slow_uptrend not implemented")

    def run_test_default_run(self, profitability):
        run_results = self._run_backtesting_with_current_config(DEFAULT_SYMBOL)
        self._assert_results(run_results, profitability)

    def run_test_slow_downtrend(self, profitability):
        run_results = self._run_backtesting_with_current_config("ICX/BTC")
        self._assert_results(run_results, profitability)

    def run_test_sharp_downtrend(self, profitability):
        run_results = self._run_backtesting_with_current_config("VEN/BTC")
        self._assert_results(run_results, profitability)

    def run_test_flat_markets(self, profitability_1, profitability_2):
        run_results = self._run_backtesting_with_current_config("NEO/BTC", True)
        self._assert_results(run_results, profitability_1)
        run_results = self._run_backtesting_with_current_config("XRB/BTC", True)
        self._assert_results(run_results, profitability_2)

    def run_test_slow_uptrend(self, profitability):
        run_results = self._run_backtesting_with_current_config("BTC/USDT")
        self._assert_results(run_results, profitability)

    @staticmethod
    def _assert_results(run_results, profitability):
        assert run_results[0] >= profitability

    def _run_backtesting_with_current_config(self, symbol, copy_config_before_use=False):
        config_to_use = copy.deepcopy(self.config) if copy_config_before_use else self.config
        filter_wanted_symbols(config_to_use, [symbol])
        bot = create_backtesting_bot(config_to_use)
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
