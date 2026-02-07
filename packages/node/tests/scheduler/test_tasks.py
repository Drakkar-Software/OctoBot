#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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
import mock
import time
import huey
import pytest
import json

import octobot_node.scheduler
import octobot_node.scheduler.tasks
import octobot_node.scheduler.octobot_lib
import tentacles.Services.Interfaces.node_api.models
import tentacles.Services.Interfaces.node_api.enums

RUN_OCTOBOT_LIB_ELEMENTS_TESTS = True
try:
    import octobot_trading.constants

    import octobot_wrapper.keywords.internal.overrides.custom_action_trading_mode as custom_action_trading_mode
except ImportError:
    # tests will be skipped if octobot_trading or octobot_wrapper are not installed
    RUN_OCTOBOT_LIB_ELEMENTS_TESTS = False

HUEY: huey.Huey = octobot_node.scheduler.SCHEDULER.INSTANCE # type: ignore

@HUEY.task()
def add_numbers(a, b):
    return a + b


@HUEY.task()
@octobot_node.scheduler.tasks.async_task
async def async_add_numbers(a, b):
    return a + b


@HUEY.task()
def reschedule_maybe(result):
    if result > 10:
        return result
    return reschedule_maybe(result * 2)

@pytest.fixture
def schedule_task():
    return tentacles.Services.Interfaces.node_api.models.Task(
        name="test_task",
        description="Test task",
        content=json.dumps(
            {
                "ACTIONS": "trade",
                "EXCHANGE_FROM": "binance",
                "ORDER_SYMBOL": "ETH/BTC",
                "ORDER_AMOUNT": 1,
                "ORDER_TYPE": "market",
                "ORDER_SIDE": "BUY",
                "SIMULATED_PORTFOLIO": {
                    "BTC": 1,
                },
            }
        ),
        type=tentacles.Services.Interfaces.node_api.models.TaskType.EXECUTE_ACTIONS.value,
    )

@pytest.fixture
def mocked_octobot_action_job():
    with mock.patch.object(
        octobot_node.scheduler.octobot_lib.OctoBotActionsJob, "run", mock.AsyncMock(
            return_value=octobot_node.scheduler.octobot_lib.OctoBotActionsJobResult(
                processed_actions=[], next_actions_description=None
            )
        )
    ) as mock_run:
        yield mock_run


@pytest.fixture
def requires_octobot_lib_elements():
    if not RUN_OCTOBOT_LIB_ELEMENTS_TESTS:
        pytest.skip(reason="OctoBot dependencies are not installed")


class TestHueyTasks:


    def setup_method(self):
        HUEY.immediate = True

    def teardown_method(self):
        HUEY.immediate = False

    def test_add_numbers(self):
        # basic huey call
        result = add_numbers(1, 2)
        assert result.get() == 3

    def test_async_task(self):
        # basic huey call with async func
        result = async_add_numbers(1, 2)
        assert result.get() == 3

    def test_execute_octobot_execution(self, schedule_task, mocked_octobot_action_job, requires_octobot_lib_elements):
        assert schedule_task.result is None
        result = octobot_node.scheduler.tasks.execute_octobot(schedule_task).get()
        assert schedule_task.result
        mocked_octobot_action_job.assert_awaited_once()
        self._assert_task_result(result, {
            "orders": [],
            "transfers": [],
        })

    @pytest.mark.timeout(5)
    def test_reshedule_octobot_execution_without_delay(self, schedule_task, mocked_octobot_action_job, requires_octobot_lib_elements):
        next_actions_description = mock.Mock(
            get_next_execution_time=mock.Mock(return_value=0),
            to_dict=mock.Mock(return_value=json.loads(schedule_task.content))
        )
        task = octobot_node.scheduler.tasks._reshedule_octobot_execution(schedule_task, next_actions_description)
        result = task.get()
        assert isinstance(result, dict)
        self._assert_task_result(result, {
            "orders": [],
            "transfers": [],
        })
        assert mocked_octobot_action_job.call_count == 1

    @pytest.mark.timeout(5)
    def test_reshedule_octobot_execution_with_delay(self, schedule_task, mocked_octobot_action_job, requires_octobot_lib_elements):
        next_actions_description = mock.Mock(
            get_next_execution_time=mock.Mock(return_value=time.time() + 1),
            to_dict=mock.Mock(return_value=json.loads(schedule_task.content))
        )
        task = octobot_node.scheduler.tasks._reshedule_octobot_execution(schedule_task, next_actions_description)
        result = task.get()
        assert result is None # task is not executed yet
        mocked_octobot_action_job.assert_not_called()

    @pytest.mark.timeout(5)
    def test_reshedule_octobot_execution_with_delay_in_the_past(self, schedule_task, mocked_octobot_action_job, requires_octobot_lib_elements):
        next_actions_description = mock.Mock(
            get_next_execution_time=mock.Mock(return_value=time.time() - 15),
            to_dict=mock.Mock(return_value=json.loads(schedule_task.content))
        )
        task = octobot_node.scheduler.tasks._reshedule_octobot_execution(schedule_task, next_actions_description)
        result = task.get()
        assert isinstance(result, dict)
        self._assert_task_result(result, {
            "orders": [],
            "transfers": [],
        })
        assert mocked_octobot_action_job.call_count == 1

    def _assert_task_result(self, result: dict, expected_result: dict):
        assert result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.STATUS.value] == tentacles.Services.Interfaces.node_api.models.TaskStatus.COMPLETED.value
        task_result = result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.RESULT.value]
        encrypted_result = not isinstance(task_result, dict)
        if encrypted_result:
            # result is encrypted, check it's a string and it's not empty
            assert isinstance(task_result, str)
            assert task_result
        else:
            assert task_result == expected_result
        if encrypted_result:
            assert isinstance(json.loads(result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.METADATA.value]), dict)
            assert result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.METADATA.value]
        else:
            assert result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.METADATA.value] is None
        assert result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.TASK.value] == {"name": "test_task"}
        assert result[tentacles.Services.Interfaces.node_api.enums.TaskResultKeys.ERROR.value] is None
