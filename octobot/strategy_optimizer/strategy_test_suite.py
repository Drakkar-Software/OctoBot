#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import copy

import octobot.api.backtesting as octobot_backtesting_api
import octobot.strategy_optimizer as octobot_strategy_optimizer
import octobot.backtesting as octobot_backtesting
import octobot_commons.constants as commons_constants

import octobot_backtesting.errors as backtesting_errors

import octobot_evaluators.constants as evaluator_constants

import octobot_trading.api as trading_api


class StrategyTestSuite(octobot_backtesting.AbstractBacktestingTest):
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
        return octobot_strategy_optimizer.TestSuiteResult(self._profitability_results,
                                                          self._trades_counts,
                                                          self.config[commons_constants.CONFIG_TRADING][
                                                              commons_constants.CONFIG_TRADER_RISK],
                                                          self.config[evaluator_constants.CONFIG_FORCED_TIME_FRAME],
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
            except Exception as e:
                self.logger.exception(e, True, f"Exception when running test {test.__name__}: {e}")
                self.exceptions.append(e)
            finally:
                self.current_progress = int((i + 1) / nb_tests * 100)
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
            exchange_manager_ids = octobot_backtesting_api.get_independent_backtesting_exchange_manager_ids(
                independent_backtesting)
            try:
                for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(exchange_manager_ids):
                    _, profitability, _, market_average_profitability, _ = \
                        trading_api.get_profitability_stats(exchange_manager)
                    # Only one exchange manager per run
                    profitability_result = (profitability, market_average_profitability)
                    trades_count += len(trading_api.get_trade_history(exchange_manager))
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
            config_to_use = copy.deepcopy(self.config)
            independent_backtesting = octobot_backtesting_api.create_independent_backtesting(
                config_to_use,
                self.tentacles_setup_config,
                [data_file_to_use],
                "",
                enforce_total_databases_max_size_after_run=False,
                enable_storage=False,
            )
            await octobot_backtesting_api.initialize_and_run_independent_backtesting(independent_backtesting, log_errors=False)
            await octobot_backtesting_api.join_independent_backtesting(independent_backtesting)
            return independent_backtesting
        except backtesting_errors.MissingTimeFrame:
            # ignore this exception: is due to missing of the only required time frame
            return independent_backtesting
        except Exception as e:
            self.logger.exception(e, True, str(e))
            return independent_backtesting
