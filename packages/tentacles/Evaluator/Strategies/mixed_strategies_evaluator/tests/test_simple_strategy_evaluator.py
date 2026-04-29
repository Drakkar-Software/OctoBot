#  Drakkar-Software OctoBot-Tentacles
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
import decimal
import pytest

import tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test as abstract_strategy_test
import tentacles.Evaluator.Strategies as Strategies
import tentacles.Trading.Mode as Mode

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def strategy_tester():
    strategy_tester_instance = SimpleStrategyEvaluatorTest()
    strategy_tester_instance.initialize(Strategies.SimpleStrategyEvaluator, Mode.DailyTradingMode)
    return strategy_tester_instance


class SimpleStrategyEvaluatorTest(abstract_strategy_test.AbstractStrategyTest):
    """
    About using this test framework:
    To be called by pytest, tests have to be called manually since the cythonized version of AbstractStrategyTest
    creates an __init__() which prevents the default pytest tests collect process
    """

    async def test_default_run(self):
        # market: -13.599062133645944
        await self.run_test_default_run(decimal.Decimal(str(-1.090)))

    async def test_slow_downtrend(self):
        # market: -13.599062133645944
        # market: -44.248234106962656
        # market: -34.87003936300901
        # market: -45.18518518518518
        await self.run_test_slow_downtrend(decimal.Decimal(str(-1.090)), decimal.Decimal(str(-36.523)),
                                           decimal.Decimal(str(-27.337)), decimal.Decimal(str(-31.155)))

    async def test_sharp_downtrend(self):
        # market: -30.271723049610415
        # market: -32.091097308488614
        await self.run_test_sharp_downtrend(decimal.Decimal(str(-24.356)), decimal.Decimal(str(-32.781)))

    async def test_flat_markets(self):
        # market: 5.052093571849795
        # market: 3.4840425531915002
        # market: -12.732688011913623
        # market: -34.64150943396227
        await self.run_test_flat_markets(decimal.Decimal(str(0.027)), decimal.Decimal(str(11.215)),
                                         decimal.Decimal(str(-13.888)), decimal.Decimal(str(-4.472)))

    async def test_slow_uptrend(self):
        # market: 32.524679029957184
        # market: 6.25
        await self.run_test_slow_uptrend(decimal.Decimal(str(15.031)), decimal.Decimal(str(0.831)))

    async def test_sharp_uptrend(self):
        # market: 24.56254050550875
        # market: 8.665472458575891
        await self.run_test_sharp_uptrend(decimal.Decimal(str(14.212)), decimal.Decimal(str(13.007)))

    async def test_up_then_down(self):
        # market: 1.1543668450702853
        await self.run_test_up_then_down(decimal.Decimal(str(2.674)))


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
