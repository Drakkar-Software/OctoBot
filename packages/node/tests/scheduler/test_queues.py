#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import mock
import pytest

import octobot_node.enums
import octobot_node.scheduler
import octobot_node.scheduler.queues as scheduler_queues_module

import tests.scheduler as scheduler_test_util


def _expected_register_calls() -> list[tuple[str, dict]]:
    return [
        (octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value, {}),
        (octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE.value, {}),
        (
            octobot_node.enums.SchedulerQueues.DBOS_CLEANUP_QUEUE.value,
            {"global_concurrency": 1},
        ),
        (
            octobot_node.enums.SchedulerQueues.GLOBAL_VIEW_QUEUE.value,
            {"global_concurrency": 1},
        ),
        (
            octobot_node.enums.SchedulerQueues.PORTFOLIO_HISTORY_QUEUE.value,
            {"global_concurrency": 1},
        ),
    ]


def _assert_register_queue_calls(register_mock: mock.Mock) -> None:
    assert register_mock.call_count == 5
    expected_calls = _expected_register_calls()
    for call_index, (expected_name, expected_kwargs) in enumerate(expected_calls):
        call = register_mock.call_args_list[call_index]
        assert call.args[0] == expected_name
        assert call.kwargs == expected_kwargs


class TestSchedulerQueueSpecs:
    def test_scheduler_queue_specs_count(self):
        assert len(scheduler_queues_module._SCHEDULER_QUEUE_SPECS) == 5


class TestRegisterSchedulerQueues:
    def test_registers_all_scheduler_queues_in_order(self):
        with mock.patch.object(
            scheduler_test_util.dbos.DBOS,
            "register_queue",
        ) as register_queue_mock:
            scheduler_test_util.register_scheduler_queues()
        _assert_register_queue_calls(register_queue_mock)


class TestRegisterSchedulerQueuesAsync:
    @pytest.mark.asyncio
    async def test_registers_all_scheduler_queues_in_order(self):
        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.register_queue_async = mock.AsyncMock()
        previous_instance = octobot_node.scheduler.SCHEDULER.INSTANCE
        octobot_node.scheduler.SCHEDULER.INSTANCE = mock_dbos_instance
        try:
            await scheduler_queues_module.register_scheduler_queues_async()
        finally:
            octobot_node.scheduler.SCHEDULER.INSTANCE = previous_instance
        _assert_register_queue_calls(mock_dbos_instance.register_queue_async)
