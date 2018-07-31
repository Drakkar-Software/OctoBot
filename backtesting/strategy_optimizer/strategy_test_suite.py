import logging


from tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test import AbstractStrategyTest
from config.cst import CONFIG_TRADER_RISK, CONFIG_TRADER, CONFIG_FORCED_EVALUATOR, CONFIG_FORCED_TIME_FRAME
from trading.exchanges.exchange_simulator.exchange_simulator import NoCandleDataForThisTimeFrameException
from backtesting.strategy_optimizer.test_suite_result import TestSuiteResult


class StrategyTestSuite(AbstractStrategyTest):

    # set to True to skip bigger scenarii and make tests faster
    SKIP_LONG_STEPS = False

    def __init__(self):
        super().__init__()
        self._profitability_results = []
        self._trades_counts = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_progress = 0

    def get_test_suite_result(self):
        return TestSuiteResult(self._profitability_results,
                               self._trades_counts,
                               self.config[CONFIG_TRADER][CONFIG_TRADER_RISK],
                               self.config[CONFIG_FORCED_TIME_FRAME],
                               self.config[CONFIG_FORCED_EVALUATOR],
                               self.strategy_evaluator_class.get_name())

    def get_progress(self):
        return self.current_progress

    def run_test_suite(self, strategy_tester):
        tests = [self.test_slow_downtrend, self.test_sharp_downtrend, self.test_flat_markets,
                 self.test_slow_uptrend, self.test_sharp_uptrend, self.test_up_then_down]
        print('| ', end='')
        nb_tests = len(tests)
        for i, test in enumerate(tests):
            try:
                test(strategy_tester)
                self.current_progress = int((i+1)/nb_tests*100)
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
        strategy_tester.run_test_slow_downtrend(None, None, None, None,
                                                StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    def test_sharp_downtrend(strategy_tester):
        strategy_tester.run_test_sharp_downtrend(None, None,
                                                 StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    def test_flat_markets(strategy_tester):
        strategy_tester.run_test_flat_markets(None, None, None, None,
                                              StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    def test_slow_uptrend(strategy_tester):
        strategy_tester.run_test_slow_uptrend(None, None)

    @staticmethod
    def test_sharp_uptrend(strategy_tester):
        strategy_tester.run_test_sharp_uptrend(None, None)

    @staticmethod
    def test_up_then_down(strategy_tester):
        strategy_tester.run_test_up_then_down(None,
                                              StrategyTestSuite.SKIP_LONG_STEPS)

    def _assert_results(self, run_results, profitability, bot):
        self._profitability_results.append(run_results)
        trader = next(iter(bot.get_exchange_trader_simulators().values()))
        self._trades_counts.append(len(trader.get_trades_manager().get_trade_history()))
