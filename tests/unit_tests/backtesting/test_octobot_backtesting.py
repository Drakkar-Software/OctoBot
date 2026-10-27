#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import pytest
from mock import Mock, patch

import octobot.backtesting as backtesting
import octobot_tentacles_manager.api as tentacles_manager_api


pytestmark = pytest.mark.asyncio


class FakeEvaluator:
    pass


def _backtesting_with_evaluators(evaluators):
    # evaluators are grouped per symbol / time frame, like OctoBotBacktesting.evaluators
    instance = backtesting.OctoBotBacktesting.__new__(backtesting.OctoBotBacktesting)
    instance.evaluators = [evaluators]
    instance.services_config = {}
    instance.logger = Mock()
    return instance


class TestCreateServices:
    async def test_logs_exception_when_service_requirements_lookup_fails(self):
        error = RuntimeError("broken requirements")
        instance = _backtesting_with_evaluators([FakeEvaluator()])
        with patch.object(
            tentacles_manager_api, "get_tentacle_classes_requirements", Mock(side_effect=error)
        ):
            await instance._create_services()

        instance.logger.exception.assert_called_once()
        logged_exception, publish_error, message = instance.logger.exception.call_args.args
        assert logged_exception is error
        assert publish_error is False
        assert "FakeEvaluator" in message
        instance.logger.error.assert_not_called()

    async def test_does_not_log_exception_when_service_requirements_lookup_succeeds(self):
        instance = _backtesting_with_evaluators([FakeEvaluator()])
        with patch.object(
            tentacles_manager_api, "get_tentacle_classes_requirements", Mock(return_value=[])
        ):
            await instance._create_services()

        instance.logger.exception.assert_not_called()
