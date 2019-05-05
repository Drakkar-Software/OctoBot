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

import copy

from tools.logging.logging_util import get_logger
from backtesting.abstract_backtesting_test import AbstractBacktestingTest, SYMBOLS, DATA_FILES, DATA_FILE_PATH
from config import CONFIG_TRADER_RISK, CONFIG_TRADING, CONFIG_FORCED_EVALUATOR, CONFIG_FORCED_TIME_FRAME, \
    CONFIG_BACKTESTING, CONFIG_BACKTESTING_DATA_FILES, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS
from trading.exchanges.exchange_simulator.exchange_simulator import NoCandleDataForThisTimeFrameException
from backtesting.strategy_optimizer.test_suite_result import TestSuiteResult
from backtesting.backtesting_util import create_backtesting_bot, start_backtesting_bot, filter_wanted_symbols
from backtesting.collector.data_file_manager import interpret_file_name, DATA_FILE_EXT
from services.web_service import WebService


class StrategyTestSuite(AbstractBacktestingTest):

    # set to True to skip bigger scenarii and make tests faster
    SKIP_LONG_STEPS = False

    def __init__(self):
        super().__init__()
        self._profitability_results = []
        self._trades_counts = []
        self.logger = get_logger(self.__class__.__name__)
        self.current_progress = 0
        self.exceptions = []

    def get_test_suite_result(self):
        return TestSuiteResult(self._profitability_results,
                               self._trades_counts,
                               self.config[CONFIG_TRADING][CONFIG_TRADER_RISK],
                               self.config[CONFIG_FORCED_TIME_FRAME],
                               self.config[CONFIG_FORCED_EVALUATOR],
                               self.strategy_evaluator_class.get_name())

    def get_progress(self):
        return self.current_progress

    def get_exceptions(self):
        return self.exceptions

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
            except NoCandleDataForThisTimeFrameException:
                pass
            except Exception as e:
                print(f"Exception when running test {test.__name__}: {e}")
                self.logger.exception(e)
                self.exceptions.append(e)
            print('#', end='')
        print(' |', end='')
        return not self.exceptions

    @staticmethod
    async def test_default_run(strategy_tester):
        await strategy_tester.run_test_default_run(None)

    @staticmethod
    async def test_slow_downtrend(strategy_tester):
        await strategy_tester.run_test_slow_downtrend(None, None, None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    async def test_sharp_downtrend(strategy_tester):
        await strategy_tester.run_test_sharp_downtrend(None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    async def test_flat_markets(strategy_tester):
        await strategy_tester.run_test_flat_markets(None, None, None, None, StrategyTestSuite.SKIP_LONG_STEPS)

    @staticmethod
    async def test_slow_uptrend(strategy_tester):
        await strategy_tester.run_test_slow_uptrend(None, None)

    @staticmethod
    async def test_sharp_uptrend(strategy_tester):
        await strategy_tester.run_test_sharp_uptrend(None, None)

    @staticmethod
    async def test_up_then_down(strategy_tester):
        await strategy_tester.run_test_up_then_down(None, StrategyTestSuite.SKIP_LONG_STEPS)

    def _assert_results(self, run_results, profitability, bot):
        self._profitability_results.append(run_results)
        trader = next(iter(bot.get_exchange_trader_simulators().values()))
        self._trades_counts.append(len(trader.get_trades_manager().get_trade_history()))

    async def _run_backtesting_with_current_config(self, symbol, data_file_to_use=None):
        config_to_use = copy.deepcopy(self.config)
        config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES] = copy.copy(DATA_FILES)
        # remove unused symbols
        symbols = {}
        for currency, details in copy.deepcopy(SYMBOLS).items():
            if symbol in details[CONFIG_CRYPTO_PAIRS]:
                symbols[currency] = details
        config_to_use[CONFIG_CRYPTO_CURRENCIES] = symbols
        if data_file_to_use is not None:
            for index, datafile in enumerate(DATA_FILES):
                _, file_symbol, _, _ = interpret_file_name(datafile)
                if symbol == file_symbol:
                    config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES][index] = \
                        DATA_FILE_PATH + data_file_to_use + DATA_FILE_EXT

        # do not activate web interface on standalone backtesting bot
        WebService.enable(config_to_use, False)
        filter_wanted_symbols(config_to_use, [symbol])
        bot = create_backtesting_bot(config_to_use)
        # debug set to False to improve performances
        return await start_backtesting_bot(bot), bot
