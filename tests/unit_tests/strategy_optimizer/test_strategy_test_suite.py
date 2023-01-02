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
import os

import mock
import builtins
import pytest

import octobot.strategy_optimizer as strategy_optimizer

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class StrategyTestSuiteMock(strategy_optimizer.StrategyTestSuite, mock.Mock):
    def __init__(self, *args, **kwargs):
        super(strategy_optimizer.StrategyTestSuite, self).__init__(*args, **kwargs)
        super(mock.Mock, self).__init__(*args, **kwargs)
        self.logger = mock.Mock()
        self.test_slow_downtrend = mock.AsyncMock()
        self.test_sharp_downtrend = mock.AsyncMock()
        self.test_flat_markets = mock.AsyncMock()
        self.test_slow_uptrend = mock.AsyncMock()
        self.test_sharp_uptrend = mock.AsyncMock()
        # will raise RuntimeError
        self.test_up_then_down = mock.AsyncMock(side_effect=RuntimeError())
        self.test_up_then_down.__name__ = "test_up_then_down"


async def test_run_test_suite():
    test_suite = StrategyTestSuiteMock()
    tester_mock = mock.Mock()
    if os.getenv('CYTHON_IGNORE'):
        return
    with mock.patch.object(builtins, "print", mock.Mock()) as print_mock:
        assert await test_suite.run_test_suite(tester_mock) is False
        calls = (test_suite.test_slow_downtrend, test_suite.test_sharp_downtrend, test_suite.test_flat_markets,
                 test_suite.test_slow_uptrend, test_suite.test_sharp_uptrend, test_suite.test_up_then_down)
        for call in calls:
            call.assert_called_once()
        assert test_suite.current_progress == 100
        assert len(test_suite.exceptions) == 1
        assert isinstance(test_suite.exceptions[0], RuntimeError)
        test_suite.logger.exception.assert_called_once()
        # once for each call and one for the beginning and the end
        assert print_mock.call_count == len(calls) + 2
