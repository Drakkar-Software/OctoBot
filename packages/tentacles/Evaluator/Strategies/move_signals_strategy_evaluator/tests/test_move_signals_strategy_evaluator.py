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
    strategy_tester_instance = MoveSignalsStrategyEvaluatorTest()
    strategy_tester_instance.initialize(Strategies.MoveSignalsStrategyEvaluator, Mode.SignalTradingMode)
    return strategy_tester_instance


class MoveSignalsStrategyEvaluatorTest(abstract_strategy_test.AbstractStrategyTest):
    """
    About using this test framework:
    To be called by pytest, tests have to be called manually since the cythonized version of AbstractStrategyTest
    creates an __init__() which prevents the default pytest tests collect process
    """

    async def test_default_run(self):
        # market: -12.052505966587105
        await self.run_test_default_run(decimal.Decimal(str(-2.549)))

    async def test_slow_downtrend(self):
        # market: -12.052505966587105
        # market: -15.195702225633141
        # market: -29.12366137549725
        # market: -32.110091743119256
        await self.run_test_slow_downtrend(decimal.Decimal(str(-2.549)), decimal.Decimal(str(-3.452)),
                                           decimal.Decimal(str(-17.393)), decimal.Decimal(str(-15.761)))

    async def test_sharp_downtrend(self):
        # market: -26.07183938094741
        # market: -32.1654501216545
        await self.run_test_sharp_downtrend(decimal.Decimal(str(-12.078)), decimal.Decimal(str(-10.3)))

    async def test_flat_markets(self):
        # market: -10.560669456066947
        # market: -3.401191658391241
        # market: -5.7854560064282765
        # market: -8.067940552016978
        await self.run_test_flat_markets(decimal.Decimal(str(-0.200)), decimal.Decimal(str(0.353)),
                                         decimal.Decimal(str(-8.126)), decimal.Decimal(str(-7.038)))

    async def test_slow_uptrend(self):
        # market: 17.203948364436457
        # market: 16.19613670133728
        await self.run_test_slow_uptrend(decimal.Decimal(str(10.278)), decimal.Decimal(str(4.299)))

    async def test_sharp_uptrend(self):
        # market: 30.881852230166828
        # market: 12.28597871355852
        await self.run_test_sharp_uptrend(decimal.Decimal(str(6.504)), decimal.Decimal(str(5.411)))

    async def test_up_then_down(self):
        # market: -6.040105108015155
        await self.run_test_up_then_down(decimal.Decimal(str(-6.691)))


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
