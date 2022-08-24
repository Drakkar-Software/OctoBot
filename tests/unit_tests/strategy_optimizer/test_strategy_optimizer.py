#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import os

import mock
import builtins

import tests.test_utils.config as test_utils_config
import octobot_commons.tests.test_config as test_config
import tentacles.Evaluator.Strategies as tentacles_strategies
import octobot.strategy_optimizer as strategy_optimizer


class StrategyTestSuiteMock(mock.Mock):
    def __init__(self, *args, **kwargs):
        super(StrategyTestSuiteMock, self).__init__(*args, **kwargs)
        self.run_test_suite = mock.AsyncMock()
        self.initialize_with_strategy = mock.Mock()

    def get_test_suite_result(self, *_, **__):
        strategy_name = tentacles_strategies.SimpleStrategyEvaluator.get_name()
        return strategy_optimizer.TestSuiteResult([(1, 0), (0, -1)], [1, 2], 1, ["tf1", "tf2"], [strategy_name], strategy_name)


def test_find_optimal_configuration():
    with mock.patch.object(strategy_optimizer, "StrategyTestSuite", StrategyTestSuiteMock()) as test_suite_mock, \
         mock.patch.object(builtins, "print", mock.Mock()) as print_mock:
        strategy_name = tentacles_strategies.SimpleStrategyEvaluator.get_name()
        optimizer = strategy_optimizer.StrategyOptimizer(test_config.load_test_config(),
                                                         test_utils_config.load_test_tentacles_config(),
                                                         strategy_name)
        optimizer.find_optimal_configuration()
        if os.getenv('CYTHON_IGNORE'):
            return
        assert optimizer.total_nb_runs == 21
        assert test_suite_mock.call_count == optimizer.total_nb_runs
        assert print_mock.call_count == optimizer.total_nb_runs * 2
        # check each call has been different
        # iterate over each second print call to check run config (each strategy optimizer run prints twice)
        for call in print_mock.call_args_list[::2]:
            assert len([c for c in print_mock.call_args_list if c == call]) == 1
