#  Drakkar-Software OctoBot-Node
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
import mock

from octobot_node.scheduler.api import (
    get_node_status,
    get_task_metrics,
    get_all_tasks,
    get_task_result,
)


class TestGetNodeStatus:
    """Tests for get_node_status function."""

    def test_get_node_status_master_node_with_redis(self) -> None:
        """Test node status for master node with Redis backend."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_REDIS_URL = "redis://localhost:6379"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 0

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = False

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["node_type"] == "master"
            assert result["backend_type"] == "redis"
            assert result["workers"] is None
            assert result["status"] == "running"
            assert result["redis_url"] == "redis://localhost:6379"
            assert result["sqlite_file"] is None

    def test_get_node_status_slave_node_with_sqlite(self) -> None:
        """Test node status for consumer node with SQLite backend."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = False
        mock_settings.SCHEDULER_REDIS_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 4

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = True
        mock_consumer.workers = 4

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["node_type"] == "consumer"
            assert result["backend_type"] == "sqlite"
            assert result["workers"] == 4
            assert result["status"] == "running"
            assert result["redis_url"] is None
            assert result["sqlite_file"] == "tasks.db"

    def test_get_node_status_slave_node_stopped(self) -> None:
        """Test node status for consumer node when consumer is stopped."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = False
        mock_settings.SCHEDULER_REDIS_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 4

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = False
        mock_consumer.workers = 4

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["node_type"] == "consumer"
            assert result["status"] == "stopped"
            assert result["workers"] == 4

    def test_get_node_status_master_node_always_running(self) -> None:
        """Test that master node is always running regardless of consumer state."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_REDIS_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 0

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = False

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["status"] == "running"
            assert result["node_type"] == "master"

    def test_get_node_status_both_master_and_consumers(self) -> None:
        """Test node status when both master mode and consumers are enabled."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_REDIS_URL = "redis://localhost:6379"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 4

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = True
        mock_consumer.workers = 4

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["node_type"] == "both"
            assert result["backend_type"] == "redis"
            assert result["workers"] == 4
            assert result["status"] == "running"

    def test_get_node_status_none(self) -> None:
        """Test node status when neither master mode nor consumers are enabled."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = False
        mock_settings.SCHEDULER_REDIS_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"
        mock_settings.SCHEDULER_WORKERS = 0

        mock_consumer = mock.Mock()
        mock_consumer.is_started.return_value = False

        with mock.patch("octobot_node.scheduler.api.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.api.CONSUMER", mock_consumer):
            result = get_node_status()

            assert result["node_type"] == "none"
            assert result["status"] == "stopped"
            assert result["workers"] is None


class TestGetTaskMetrics:
    """Tests for get_task_metrics function."""

    def test_get_task_metrics_success(self) -> None:
        """Test successful retrieval of task metrics."""
        mock_huey = mock.Mock()
        mock_huey.pending_count.return_value = 5
        mock_huey.scheduled_count.return_value = 3
        mock_huey.result_count.return_value = 10

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_huey
        mock_scheduler.get_periodic_tasks.return_value = [
            {"id": "task1"},
            {"id": "task2"},
        ]

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_task_metrics()

            assert result["pending"] == 5
            assert result["scheduled"] == 5  # 3 + 2 periodic tasks
            assert result["results"] == 10
            mock_huey.pending_count.assert_called_once()
            mock_huey.scheduled_count.assert_called_once()
            mock_huey.result_count.assert_called_once()
            mock_scheduler.get_periodic_tasks.assert_called_once()

    def test_get_task_metrics_uninitialized_scheduler(self) -> None:
        """Test task metrics when scheduler is not initialized."""
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = None

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_task_metrics()

            assert result == {"pending": 0, "scheduled": 0, "results": 0}

    def test_get_task_metrics_exception_handling(self) -> None:
        """Test task metrics when an exception occurs."""
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock()
        mock_scheduler.INSTANCE.pending_count.side_effect = Exception("Database error")

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_task_metrics()

            assert result == {"pending": 0, "scheduled": 0, "results": 0}

    def test_get_task_metrics_no_periodic_tasks(self) -> None:
        """Test task metrics when there are no periodic tasks."""
        mock_huey = mock.Mock()
        mock_huey.pending_count.return_value = 2
        mock_huey.scheduled_count.return_value = 1
        mock_huey.result_count.return_value = 5

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_huey
        mock_scheduler.get_periodic_tasks.return_value = []

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_task_metrics()

            assert result["pending"] == 2
            assert result["scheduled"] == 1
            assert result["results"] == 5


class TestGetAllTasks:
    """Tests for get_all_tasks function."""

    def test_get_all_tasks_success(self) -> None:
        """Test successful retrieval of all tasks."""
        periodic_tasks = [{"id": "periodic1", "status": "periodic"}]
        pending_tasks = [{"id": "pending1", "status": "pending"}]
        scheduled_tasks = [{"id": "scheduled1", "status": "scheduled"}]
        result_tasks = [{"id": "result1", "status": "completed"}]

        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks.return_value = periodic_tasks
        mock_scheduler.get_pending_tasks.return_value = pending_tasks
        mock_scheduler.get_scheduled_tasks.return_value = scheduled_tasks
        mock_scheduler.get_results.return_value = result_tasks

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_all_tasks()

            assert len(result) == 4
            assert periodic_tasks[0] in result
            assert pending_tasks[0] in result
            assert scheduled_tasks[0] in result
            assert result_tasks[0] in result
            mock_scheduler.get_periodic_tasks.assert_called_once()
            mock_scheduler.get_pending_tasks.assert_called_once()
            mock_scheduler.get_scheduled_tasks.assert_called_once()
            mock_scheduler.get_results.assert_called_once()

    def test_get_all_tasks_empty(self) -> None:
        """Test get_all_tasks when there are no tasks."""
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks.return_value = []
        mock_scheduler.get_pending_tasks.return_value = []
        mock_scheduler.get_scheduled_tasks.return_value = []
        mock_scheduler.get_results.return_value = []

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_all_tasks()

            assert result == []

    def test_get_all_tasks_exception_handling(self) -> None:
        """Test get_all_tasks when an exception occurs."""
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks.side_effect = Exception("Database error")

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_all_tasks()

            assert result == []

    def test_get_all_tasks_partial_exception(self) -> None:
        """Test get_all_tasks when some methods fail but others succeed."""
        periodic_tasks = [{"id": "periodic1"}]
        pending_tasks = [{"id": "pending1"}]

        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks.return_value = periodic_tasks
        mock_scheduler.get_pending_tasks.return_value = pending_tasks
        mock_scheduler.get_scheduled_tasks.side_effect = Exception("Error")
        mock_scheduler.get_results.return_value = []

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = get_all_tasks()

            assert len(result) == 2
            assert periodic_tasks[0] in result
            assert pending_tasks[0] in result


class TestGetTaskResult:
    """Tests for get_task_result function."""

    @pytest.mark.asyncio
    async def test_get_task_result_completed(self) -> None:
        """Test get_task_result for a completed task."""
        task_id = "task-123"
        result_data = {"status": "success", "output": "completed"}

        mock_result = mock.Mock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = result_data

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock()
        mock_scheduler.INSTANCE.result.return_value = mock_result

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result["status"] == "completed"
            assert result["data"] == result_data
            mock_scheduler.INSTANCE.result.assert_called_once_with(task_id)
            mock_result.ready.assert_called_once()
            mock_result.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_result_pending(self) -> None:
        """Test get_task_result for a pending task."""
        task_id = "task-456"

        mock_result = mock.Mock()
        mock_result.ready.return_value = False

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock()
        mock_scheduler.INSTANCE.result.return_value = mock_result

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result["status"] == "pending or running"
            assert "data" not in result
            mock_scheduler.INSTANCE.result.assert_called_once_with(task_id)
            mock_result.ready.assert_called_once()
            mock_result.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_result_not_found(self) -> None:
        """Test get_task_result for a task that doesn't exist."""
        task_id = "task-789"

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock()
        mock_scheduler.INSTANCE.result.return_value = None

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result == {"error": "task not found"}
            mock_scheduler.INSTANCE.result.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_result_running(self) -> None:
        """Test get_task_result for a running task."""
        task_id = "task-running"

        mock_result = mock.Mock()
        mock_result.ready.return_value = False

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock()
        mock_scheduler.INSTANCE.result.return_value = mock_result

        with mock.patch("octobot_node.scheduler.api.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result["status"] == "pending or running"