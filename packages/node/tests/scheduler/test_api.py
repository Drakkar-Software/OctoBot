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

from tests.scheduler import temp_dbos_scheduler


class TestGetNodeStatus:
    """Tests for get_node_status function."""

    def test_get_node_status_master_node_with_postgres(self) -> None:
        """Test node status for master node with Postgres backend."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_POSTGRES_URL = "postgresql://localhost/db"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        with mock.patch("octobot_node.config.settings", mock_settings):
            result = get_node_status()

            assert result["node_type"] == "both"
            assert result["backend_type"] == "postgres"
            assert result["workers"] == 1
            assert result["status"] == "running"
            assert result["redis_url"] is None
            assert result["sqlite_file"] is None

    def test_get_node_status_master_node_always_running(self) -> None:
        """Test that master node is always running regardless of consumer state."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_POSTGRES_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.Mock(_launched=False)

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = get_node_status()

            assert result["status"] == "running"
            assert result["node_type"] == "both"

    def test_get_node_status_both_master_and_consumers(self) -> None:
        """Test node status when both master mode and consumers are enabled."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_POSTGRES_URL = "postgresql://localhost/db"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        with mock.patch("octobot_node.config.settings", mock_settings):
            result = get_node_status()

            assert result["node_type"] == "both"
            assert result["backend_type"] == "postgres"
            assert result["workers"] == 1 # multi workers are not supported yet
            assert result["status"] == "running"

    def test_get_node_status_none(self) -> None:
        """Test node status when neither master mode nor consumers are enabled."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = False
        mock_settings.CONSUMER_ONLY = False
        mock_settings.SCHEDULER_POSTGRES_URL = None
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        with mock.patch("octobot_node.config.settings", mock_settings):
            result = get_node_status()

            assert result["node_type"] == "none"
            assert result["status"] == "stopped"
            assert result["workers"] is 0


class TestGetTaskMetrics:
    """Tests for get_task_metrics function."""

    @pytest.mark.asyncio
    async def test_get_task_metrics_success(self, temp_dbos_scheduler) -> None:
        """Test successful retrieval of task metrics."""
        call_responses = [[mock.Mock()] * 5, [mock.Mock()] * 10]
        call_idx = [0]

        async def mock_list_workflows(*args, **kwargs):
            result = call_responses[call_idx[0]]
            call_idx[0] += 1
            return result

        mock_get_periodic = mock.AsyncMock(return_value=[
            {"id": "task1"},
            {"id": "task2"},
        ])

        with mock.patch.object(
            temp_dbos_scheduler.INSTANCE, "list_workflows_async", side_effect=mock_list_workflows
        ), mock.patch.object(temp_dbos_scheduler, "get_periodic_tasks", mock_get_periodic):
            result = await get_task_metrics()

            assert result["pending"] == 5
            assert result["scheduled"] == 2
            assert result["results"] == 10
            mock_get_periodic.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_metrics_uninitialized_scheduler(self) -> None:
        """Test task metrics when scheduler is not initialized."""
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = None

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

            assert result == {"pending": 0, "scheduled": 0, "results": 0}

    @pytest.mark.asyncio
    async def test_get_task_metrics_exception_handling(self) -> None:
        """Test task metrics when an exception occurs."""
        mock_instance = mock.AsyncMock()
        mock_instance.list_workflows_async.side_effect = Exception("Database error")

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

            assert result == {"pending": 0, "scheduled": 0, "results": 0}

    @pytest.mark.asyncio
    async def test_get_task_metrics_no_periodic_tasks(self) -> None:
        """Test task metrics when there are no periodic tasks."""
        call_responses = [[mock.Mock()] * 2, [mock.Mock()] * 5]
        call_idx = [0]

        async def mock_list_workflows(*args, **kwargs):
            result = call_responses[call_idx[0]]
            call_idx[0] += 1
            return result

        mock_instance = mock.AsyncMock()
        mock_instance.list_workflows_async.side_effect = mock_list_workflows

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

            assert result["pending"] == 2
            assert result["scheduled"] == 0
            assert result["results"] == 5


class TestGetAllTasks:
    """Tests for get_all_tasks function."""

    @pytest.mark.asyncio
    async def test_get_all_tasks_success(self, temp_dbos_scheduler) -> None:
        """Test successful retrieval of all tasks."""
        periodic_tasks = [{"id": "periodic1", "status": "periodic"}]
        pending_tasks = [{"id": "pending1", "status": "pending"}]
        scheduled_tasks = [{"id": "scheduled1", "status": "scheduled"}]
        result_tasks = [{"id": "result1", "status": "completed"}]

        with mock.patch.object(
            temp_dbos_scheduler, "get_periodic_tasks", mock.AsyncMock(return_value=periodic_tasks)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_pending_tasks", mock.AsyncMock(return_value=pending_tasks)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_scheduled_tasks", mock.AsyncMock(return_value=scheduled_tasks)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_results", mock.AsyncMock(return_value=result_tasks)
        ):
            result = await get_all_tasks()

            assert len(result) == 4
            assert periodic_tasks[0] in result
            assert pending_tasks[0] in result
            assert scheduled_tasks[0] in result
            assert result_tasks[0] in result

    @pytest.mark.asyncio
    async def test_get_all_tasks_empty(self) -> None:
        """Test get_all_tasks when there are no tasks."""
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_pending_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_scheduled_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_results = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_all_tasks()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_all_tasks_exception_handling(self) -> None:
        """Test get_all_tasks when an exception occurs."""
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(side_effect=Exception("Database error"))
        mock_scheduler.get_pending_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_scheduled_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_results = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_all_tasks()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_all_tasks_partial_exception(self) -> None:
        """Test get_all_tasks when one method fails - gather fails entirely, returns []."""
        periodic_tasks = [{"id": "periodic1"}]
        pending_tasks = [{"id": "pending1"}]

        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=periodic_tasks)
        mock_scheduler.get_pending_tasks = mock.AsyncMock(return_value=pending_tasks)
        mock_scheduler.get_scheduled_tasks = mock.AsyncMock(side_effect=Exception("Error"))
        mock_scheduler.get_results = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_all_tasks()

            assert result == []


class TestGetTaskResult:
    """Tests for get_task_result function."""

    @pytest.mark.asyncio
    async def test_get_task_result_completed(self, temp_dbos_scheduler) -> None:
        """Test get_task_result for a completed task."""
        task_id = "task-123"
        result_data = {"status": "success", "output": "completed"}

        mock_handle = mock.AsyncMock()
        mock_handle.get_status = mock.AsyncMock(return_value=mock.Mock(status="SUCCESS"))
        mock_handle.get_result = mock.AsyncMock(return_value=result_data)

        mock_retrieve = mock.AsyncMock(return_value=mock_handle)

        with mock.patch.object(
            temp_dbos_scheduler.INSTANCE, "retrieve_workflow_async", mock_retrieve
        ):
            result = await get_task_result(task_id)

            assert result["status"] == "completed"
            assert result["data"] == result_data
            mock_retrieve.assert_called_once_with(task_id)
            mock_handle.get_status.assert_called_once()
            mock_handle.get_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_result_pending(self) -> None:
        """Test get_task_result for a pending task."""
        task_id = "task-456"

        mock_handle = mock.AsyncMock()
        mock_handle.get_status = mock.AsyncMock(return_value=mock.Mock(status="PENDING"))

        mock_instance = mock.AsyncMock()
        mock_instance.retrieve_workflow_async = mock.AsyncMock(return_value=mock_handle)

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result["status"] == "pending or running"
            assert "data" not in result
            mock_instance.retrieve_workflow_async.assert_called_once_with(task_id)
            mock_handle.get_status.assert_called_once()
            mock_handle.get_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_result_not_found(self) -> None:
        """Test get_task_result for a task that doesn't exist."""
        task_id = "task-789"

        mock_instance = mock.AsyncMock()
        mock_instance.retrieve_workflow_async = mock.AsyncMock(side_effect=Exception("not found"))

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result == {"error": "task not found"}
            mock_instance.retrieve_workflow_async.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_result_running(self) -> None:
        """Test get_task_result for a running task."""
        task_id = "task-running"

        mock_handle = mock.AsyncMock()
        mock_handle.get_status = mock.AsyncMock(return_value=mock.Mock(status="PENDING"))

        mock_instance = mock.AsyncMock()
        mock_instance.retrieve_workflow_async = mock.AsyncMock(return_value=mock_handle)

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_result(task_id)

            assert result["status"] == "pending or running"