#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import json
import mock
import pytest

import octobot_node.models
import octobot_node.scheduler.tasks

from tests.scheduler import temp_dbos_scheduler

@pytest.fixture
def schedule_task():
    return octobot_node.models.Task(
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
        type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
    )


class TestTriggerTask:
    """Tests for trigger_task function."""

    @pytest.mark.asyncio
    async def test_trigger_all_task_types(self, schedule_task, temp_dbos_scheduler):
        """Test trigger_task for START_OCTOBOT type."""
        for task_type in octobot_node.models.TaskType:
            schedule_task.type = task_type.value
            with mock.patch.object(
                temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE, "enqueue_async", mock.AsyncMock()
            ) as mock_enqueue_async:
                result = await octobot_node.scheduler.tasks.trigger_task(schedule_task)
                assert result is True
                mock_enqueue_async.assert_called_once()
                call_kwargs = mock_enqueue_async.call_args[1]
                assert "inputs" in call_kwargs
                assert len(call_kwargs["inputs"]) == 1
                inputs = call_kwargs["inputs"]
                assert inputs["task"] == schedule_task.model_dump(exclude_defaults=True)
        with pytest.raises(ValueError, match="Unsupported task type"):
            with mock.patch.object(
                temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE, "enqueue_async", mock.AsyncMock()
            ) as mock_enqueue_async:
                schedule_task.type = "invalid_type"
                await octobot_node.scheduler.tasks.trigger_task(schedule_task)
                mock_enqueue_async.assert_not_called()
