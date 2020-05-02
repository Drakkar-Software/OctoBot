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
from copy import deepcopy

from octobot.api.backtesting import create_independent_backtesting, \
    initialize_and_run_independent_backtesting, get_independent_backtesting_exchange_manager_ids, \
    join_independent_backtesting
from octobot.strategy_optimizer.test_suite_result import TestSuiteResult
from octobot_backtesting.data import MissingTimeFrame
from octobot.backtesting.abstract_backtesting_test import AbstractBacktestingTest
from octobot_evaluators.constants import CONFIG_FORCED_TIME_FRAME
from octobot_trading.constants import CONFIG_TRADER_RISK, CONFIG_TRADING
from octobot_trading.api.exchange import get_exchange_managers_from_exchange_ids
from octobot_trading.api.profitability import get_profitability_stats
from octobot_trading.api.trades import get_trade_history


class StrategyTestSuite(AbstractBacktestingTest):

    # set to True to skip bigger scenarii and make tests faster
    SKIP_LONG_STEPS = False

    def __init__(self):
        super().__init__()
        self._profitability_results = []
        self._trades_counts = []
        self.current_progress = 0
        self.exceptions = []
        self.evaluators = []

    def get_test_suite_result(self):
        return TestSuiteResult(self._profitability_results,
                               self._trades_counts,
                               self.config[CONFIG_TRADING][CONFIG_TRADER_RISK],
                               self.config[CONFIG_FORCED_TIME_FRAME],
                               self.evaluators,
                               self.strategy_evaluator_class.get_name())

    async def run_test_suite(self, strategy_tester):
        self.exceptions = []
        tests = [self.test_slow_downtrend, self.test_sharp_downtrend, self.test_flat_markets,
                 self.test_slow_uptrend, self.test_sharp_uptrend, self.test_up_then_down]
        print('| ', end='')
        nb_tests = len(tests)
        for i, test in enumerate(tests):
            try:
                await test(strategy_tester)
                self.current_progress = int((i+1)/nb_tests*100)
            except Exception as e:
                self.logger.exception(e, True, f"Exception when running test {test.__name__}: {e}")
                self.exceptions.append(e)
            print('#', end='')
        print(' |', end='')
        return not self.exceptions

    async def test_default_run(self, strategy_tester):
        await strategy_tester.run_test_default_run(None)

    async def test_slow_downtrend(self, strategy_tester):
        await strategy_tester.run_test_slow_downtrend(None, None, None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    async def test_sharp_downtrend(self, strategy_tester):
        await strategy_tester.run_test_sharp_downtrend(None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    async def test_flat_markets(self, strategy_tester):
        await strategy_tester.run_test_flat_markets(None, None, None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    async def test_slow_uptrend(self, strategy_tester):
        await strategy_tester.run_test_slow_uptrend(None, None)

    async def test_sharp_uptrend(self, strategy_tester):
        await strategy_tester.run_test_sharp_uptrend(None, None)

    async def test_up_then_down(self, strategy_tester):
        await strategy_tester.run_test_up_then_down(None, StrategyTestSuite.SKIP_LONG_STEPS)

    def _handle_results(self, independent_backtesting, profitability):
        trades_count = 0
        profitability_result = None
        skip_this_run = False
        if independent_backtesting is not None:
            exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
            try:
                for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
                    _, profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
                    # Only one exchange manager per run
                    profitability_result = (profitability, market_average_profitability)
                    trades_count += len(get_trade_history(exchange_manager))
            except (AttributeError, KeyError):
                skip_this_run = True
            if not skip_this_run:
                if profitability_result is None:
                    raise RuntimeError("Error with independent backtesting: no available exchange manager")
                self._profitability_results.append(profitability_result)
                self._trades_counts.append(trades_count)

    async def _run_backtesting_with_current_config(self, data_file_to_use):
        independent_backtesting = None
        try:
            config_to_use = deepcopy(self.config)
            independent_backtesting = create_independent_backtesting(config_to_use,
                                                                     self.tentacles_setup_config,
                                                                     [data_file_to_use],
                                                                     "")
            await initialize_and_run_independent_backtesting(independent_backtesting, log_errors=False)
            await join_independent_backtesting(independent_backtesting)
            return independent_backtesting
        except MissingTimeFrame:
            # ignore this exception: is due to missing of the only required time frame
            return independent_backtesting
        except Exception as e:
            self.logger.exception(e, True, str(e))
            return independent_backtesting
