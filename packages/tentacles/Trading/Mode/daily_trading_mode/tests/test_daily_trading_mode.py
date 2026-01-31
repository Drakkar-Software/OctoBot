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
import pytest

import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.api as tentacles_manager_api
import tests.test_utils.memory_check_util as memory_check_util
import tentacles.Evaluator.Strategies as Strategies
import tentacles.Evaluator.TA as Evaluator
import tentacles.Trading.Mode as Mode

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_run_independent_backtestings_with_memory_check():
    tentacles_setup_config = tentacles_manager_api.create_tentacles_setup_config_with_tentacles(Mode.DailyTradingMode,
                                                                                                Strategies.SimpleStrategyEvaluator,
                                                                                                Evaluator.RSIMomentumEvaluator,
                                                                                                Evaluator.DoubleMovingAverageTrendEvaluator)
    await memory_check_util.run_independent_backtestings_with_memory_check(test_config.load_test_config(),
                                                                           tentacles_setup_config)
