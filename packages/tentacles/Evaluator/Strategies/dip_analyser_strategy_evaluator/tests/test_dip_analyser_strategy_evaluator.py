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
import pytest
import decimal

import tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test as abstract_strategy_test
import tentacles.Evaluator.Strategies as Strategies
import tentacles.Trading.Mode as Mode

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def strategy_tester():
    strategy_tester_instance = DipAnalyserStrategiesEvaluatorTest()
    strategy_tester_instance.initialize(Strategies.DipAnalyserStrategyEvaluator, Mode.DipAnalyserTradingMode)
    return strategy_tester_instance


class DipAnalyserStrategiesEvaluatorTest(abstract_strategy_test.AbstractStrategyTest):
    """
    About using this test framework:
    To be called by pytest, tests have to be called manually since the cythonized version of AbstractStrategyTest
    creates an __init__() which prevents the default pytest tests collect process
    """

    # Careful with results here, unlike other strategy tests, this one uses only the 4h timeframe, therefore results
    # are not comparable with regular 1h timeframes strategy tests

    # Cannot use bittrex data since they are not providing 4h timeframe data

    # test_full_mixed_strategies_evaluator.py with only 4h timeframe results are provided for comparison:
    # format: results: (bot profitability, market average profitability)

    async def test_default_run(self):
        # market: -49.25407390406244
        await self.run_test_default_run(decimal.Decimal(str(-24.612)))

    async def test_slow_downtrend(self):
        # market: -49.25407390406244
        # market: -47.50593824228029
        await self.run_test_slow_downtrend(decimal.Decimal(str(-24.612)), decimal.Decimal(str(-33.601)), None, None, skip_extended=True)

    async def test_sharp_downtrend(self):
        # market: -34.67997135795625
        await self.run_test_sharp_downtrend(decimal.Decimal(str(-21.634)), None, skip_extended=True)

    async def test_flat_markets(self):
        # market: -38.07647740440325
        # market: -53.87077652637819
        await self.run_test_flat_markets(decimal.Decimal(str(-20.577)), decimal.Decimal(str(-32.756)), None, None, skip_extended=True)

    async def test_slow_uptrend(self):
        # market: 11.32644122514472
        # market: -36.64596273291926
        await self.run_test_slow_uptrend(decimal.Decimal(str(11.326)), decimal.Decimal(str(-14.248)))

    async def test_sharp_uptrend(self):
        # market: -17.047906776003458
        # market: -18.25837965302341
        await self.run_test_sharp_uptrend(decimal.Decimal(str(3.607)), decimal.Decimal(str(10.956)))

    async def test_up_then_down(self):
        await self.run_test_up_then_down(None, skip_extended=True)


async def test_default_run(strategy_tester):
    await strategy_tester.test_default_run()


async def test_slow_downtrend(strategy_tester):
    await strategy_tester.test_slow_downtrend()


async def test_sharp_downtrend(strategy_tester):
    await strategy_tester.test_sharp_downtrend()


async def test_flat_markets(strategy_tester):
    await strategy_tester.test_flat_markets()


async def test_slow_uptrend(strategy_tester):
    await strategy_tester.test_slow_uptrend()


async def test_sharp_uptrend(strategy_tester):
    await strategy_tester.test_sharp_uptrend()


async def test_up_then_down(strategy_tester):
    await strategy_tester.test_up_then_down()
