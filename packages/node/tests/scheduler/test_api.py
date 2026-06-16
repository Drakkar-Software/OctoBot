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

import json
import pytest
import mock
from octobot_node.models import Execution, Task, TaskStatus
from octobot_node.scheduler.api import (
    get_node_status,
    get_task_metrics,
    get_all_tasks,
    get_task_result,
    get_tasks_export_results,
)

from tests.scheduler import temp_dbos_scheduler


def _make_wf_status(workflow_id: str, status: str, user_id: str = "0xaaa") -> mock.Mock:
    """Create a mock WorkflowStatus with user_id baked into the input field."""
    import octobot_node.enums as octobot_node_enums
    import octobot_node.scheduler.workflows.params as params
    import octobot_node.models as models
    task = models.Task(
        name="t", content=None, type="execute_actions", user_id=user_id
    )
    inputs = params.AutomationWorkflowInputs(task=task)
    wf = mock.Mock()
    wf.workflow_id = workflow_id
    wf.status = status
    wf.queue_name = octobot_node_enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value
    wf.input = {
        "args": [inputs.to_dict(include_default_values=False)],
        "kwargs": {},
    }
    wf.created_at = None
    wf.updated_at = None
    return wf


def _scheduler_stub_for_get_node_status(
    *,
    consumer_launched: bool | None = None,
) -> mock.Mock:
    """``octobot_node.scheduler.SCHEDULER`` stand-in so ``get_node_status`` skips the real singleton."""
    scheduler_stub = mock.Mock()
    if consumer_launched is None:
        scheduler_stub.INSTANCE = None
    else:
        scheduler_stub.INSTANCE = mock.Mock(_launched=consumer_launched)
    return scheduler_stub


class TestGetNodeStatus:
    """Tests for get_node_status function."""

    def test_get_node_status_master_node_with_postgres(self) -> None:
        """Test node status for master node with Postgres backend."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_POSTGRES_URL = "postgresql://localhost/db"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.SCHEDULER",
                 _scheduler_stub_for_get_node_status(),
             ):
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

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.SCHEDULER",
                 _scheduler_stub_for_get_node_status(consumer_launched=False),
             ):
            result = get_node_status()

            assert result["status"] == "running"
            assert result["node_type"] == "both"

    def test_get_node_status_both_master_and_consumers(self) -> None:
        """Test node status when both master mode and consumers are enabled."""
        mock_settings = mock.Mock()
        mock_settings.IS_MASTER_MODE = True
        mock_settings.SCHEDULER_POSTGRES_URL = "postgresql://localhost/db"
        mock_settings.SCHEDULER_SQLITE_FILE = "tasks.db"

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.SCHEDULER",
                 _scheduler_stub_for_get_node_status(),
             ):
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

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.SCHEDULER",
                 _scheduler_stub_for_get_node_status(),
             ):
            result = get_node_status()

            assert result["node_type"] == "none"
            assert result["status"] == "stopped"
            assert result["workers"] is 0


class TestGetTaskMetrics:
    """Tests for get_task_metrics function."""

    @pytest.mark.asyncio
    async def test_get_task_metrics_success(self) -> None:
        """Test successful retrieval of task metrics via cheap status counts (no load_output)."""
        import dbos

        pending_wf = [
            _make_wf_status(f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb{i}", dbos.WorkflowStatusString.PENDING.value)
            for i in range(5)
        ]
        result_wf = [
            _make_wf_status(f"cccccccc-cccc-cccc-cccc-ccccccccccc{i}", dbos.WorkflowStatusString.SUCCESS.value)
            for i in range(10)
        ]

        mock_instance = mock.AsyncMock()

        def list_side_effect(status=None, **kwargs):
            if dbos.WorkflowStatusString.PENDING.value in (status or []):
                return pending_wf
            return result_wf

        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=list_side_effect)
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

        assert result["pending"] == 5
        assert result["scheduled"] == 0
        assert result["results"] == 10
        for call in mock_instance.list_workflows_async.call_args_list:
            assert call.kwargs.get("load_output") is False

    @pytest.mark.asyncio
    async def test_get_task_metrics_wallet_scoped(self) -> None:
        """Test wallet-scoped metrics: only count tasks for the matching wallet, no crypto."""
        import dbos

        my_wallet = "0xmine"
        other_wallet = "0xother"

        pending_wf = [
            _make_wf_status(f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb{i}", dbos.WorkflowStatusString.PENDING.value,
                            user_id=my_wallet if i < 2 else other_wallet)
            for i in range(4)
        ]
        result_wf = [
            _make_wf_status(f"cccccccc-cccc-cccc-cccc-ccccccccccc{i}", dbos.WorkflowStatusString.SUCCESS.value,
                            user_id=my_wallet if i < 3 else other_wallet)
            for i in range(5)
        ]

        mock_instance = mock.AsyncMock()

        def list_side_effect(status=None, **kwargs):
            if dbos.WorkflowStatusString.PENDING.value in (status or []):
                return pending_wf
            return result_wf

        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=list_side_effect)
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler), \
             mock.patch("octobot_node.scheduler.encryption.encrypt_task_result") as mock_crypto:
            result = await get_task_metrics(user_id=my_wallet)

        assert result["pending"] == 2    # only 0xmine
        assert result["results"] == 3    # only 0xmine
        mock_crypto.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_metrics_counts_legacy_and_unparseable_for_every_wallet(self) -> None:
        """Regression: tasks with no user_id (legacy) or unparseable input must count
        toward every wallet's metrics — never silently dropped (that hid all errored tasks).
        """
        import dbos
        import octobot_node.enums as octobot_node_enums

        legacy_wf = _make_wf_status("dddddddd-dddd-dddd-dddd-ddddddddddd1",
                                     dbos.WorkflowStatusString.SUCCESS.value, user_id=None)
        unparseable_wf = mock.Mock()
        unparseable_wf.workflow_id = "dddddddd-dddd-dddd-dddd-ddddddddddd2"
        unparseable_wf.status = dbos.WorkflowStatusString.SUCCESS.value
        unparseable_wf.queue_name = octobot_node_enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value
        unparseable_wf.input = {"args": [], "kwargs": {}}  # nothing parseable
        unparseable_wf.created_at = None
        unparseable_wf.updated_at = None
        other_wf = _make_wf_status("dddddddd-dddd-dddd-dddd-ddddddddddd3",
                                    dbos.WorkflowStatusString.SUCCESS.value, user_id="0xother")

        mock_instance = mock.AsyncMock()

        def list_side_effect(status=None, **kwargs):
            if dbos.WorkflowStatusString.PENDING.value in (status or []):
                return []
            return [legacy_wf, unparseable_wf, other_wf]

        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=list_side_effect)
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics(user_id="0xmine")

        # legacy + unparseable kept (2), explicit other_wallet dropped (1)
        assert result["results"] == 2

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
        """Test task metrics when list_workflows_async raises."""
        mock_instance = mock.AsyncMock()
        mock_instance.list_workflows_async.side_effect = Exception("Database error")

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

            assert result == {"pending": 0, "scheduled": 0, "results": 0}

    @pytest.mark.asyncio
    async def test_get_task_metrics_no_periodic_tasks(self) -> None:
        """Test task metrics when there are no periodic tasks (scheduled always 0)."""
        import dbos

        pending_wf = [
            _make_wf_status(f"dddddddd-dddd-dddd-dddd-ddddddddddd{i}", dbos.WorkflowStatusString.PENDING.value)
            for i in range(2)
        ]
        result_wf = [
            _make_wf_status(f"eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee{i}", dbos.WorkflowStatusString.SUCCESS.value)
            for i in range(5)
        ]

        mock_instance = mock.AsyncMock()

        def list_side_effect(status=None, **kwargs):
            if dbos.WorkflowStatusString.PENDING.value in (status or []):
                return pending_wf
            return result_wf

        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=list_side_effect)
        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_task_metrics()

            assert result["pending"] == 2
            assert result["scheduled"] == 0
            assert result["results"] == 5


class TestGetAllTasks:
    """Tests for get_all_tasks function."""

    @pytest.mark.asyncio
    async def test_get_all_tasks_success(self, temp_dbos_scheduler) -> None:
        """Test successful retrieval of all tasks with distinct IDs produces one Task per Execution."""
        periodic_executions = [Execution(id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", status=TaskStatus.PERIODIC)]
        pending_executions = [Execution(id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", status=TaskStatus.PENDING)]
        scheduled_executions = [Execution(id="cccccccc-cccc-cccc-cccc-cccccccccccc", status=TaskStatus.SCHEDULED)]
        result_executions = [Execution(id="dddddddd-dddd-dddd-dddd-dddddddddddd", status=TaskStatus.COMPLETED)]

        with mock.patch.object(
            temp_dbos_scheduler, "get_periodic_tasks", mock.AsyncMock(return_value=periodic_executions)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_pending_tasks", mock.AsyncMock(return_value=pending_executions)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_scheduled_tasks", mock.AsyncMock(return_value=scheduled_executions)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_results", mock.AsyncMock(return_value=result_executions)
        ):
            result = await get_all_tasks()

            assert len(result) == 4
            assert all(isinstance(t, Task) for t in result)
            assert all(len(t.executions) == 1 for t in result)
            task_ids = {t.id for t in result}
            assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" in task_ids
            assert "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" in task_ids
            assert "cccccccc-cccc-cccc-cccc-cccccccccccc" in task_ids
            assert "dddddddd-dddd-dddd-dddd-dddddddddddd" in task_ids

    @pytest.mark.asyncio
    async def test_get_all_tasks_merges_same_id(self, temp_dbos_scheduler) -> None:
        """Test that executions sharing the same parent ID are merged into a single Task."""
        parent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        child_suffix = "_child_step_1"
        pending_executions = [Execution(id=parent_id, status=TaskStatus.PENDING, name="my-task")]
        result_executions = [Execution(id=f"{parent_id}{child_suffix}", status=TaskStatus.COMPLETED, name="my-task")]

        with mock.patch.object(
            temp_dbos_scheduler, "get_periodic_tasks", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            temp_dbos_scheduler, "get_pending_tasks", mock.AsyncMock(return_value=pending_executions)
        ), mock.patch.object(
            temp_dbos_scheduler, "get_scheduled_tasks", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            temp_dbos_scheduler, "get_results", mock.AsyncMock(return_value=result_executions)
        ):
            result = await get_all_tasks()

            assert len(result) == 1
            task = result[0]
            assert isinstance(task, Task)
            assert task.id == parent_id
            assert len(task.executions) == 2
            assert any(e.status == TaskStatus.PENDING for e in task.executions)

    @pytest.mark.asyncio
    async def test_get_all_tasks_active_execution_latest_completed(self, temp_dbos_scheduler) -> None:
        """Test that when no pending execution, the latest completed_at is used as active."""
        import datetime
        parent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        older = Execution(
            id=f"{parent_id}_old",
            status=TaskStatus.COMPLETED,
            name="old-run",
            completed_at=datetime.datetime(2025, 1, 1),
        )
        newer = Execution(
            id=f"{parent_id}_new",
            status=TaskStatus.COMPLETED,
            name="new-run",
            completed_at=datetime.datetime(2025, 6, 1),
        )

        with mock.patch.object(
            temp_dbos_scheduler, "get_periodic_tasks", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            temp_dbos_scheduler, "get_pending_tasks", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            temp_dbos_scheduler, "get_scheduled_tasks", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            temp_dbos_scheduler, "get_results", mock.AsyncMock(return_value=[older, newer])
        ):
            result = await get_all_tasks()

            assert len(result) == 1
            assert result[0].name == "new-run"

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
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=[Execution(id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")])
        mock_scheduler.get_pending_tasks = mock.AsyncMock(return_value=[Execution(id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")])
        mock_scheduler.get_scheduled_tasks = mock.AsyncMock(side_effect=Exception("Error"))
        mock_scheduler.get_results = mock.AsyncMock(return_value=[])

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_all_tasks()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_all_tasks_wallet_filter_passed_to_scheduler(self, temp_dbos_scheduler) -> None:
        """Test that user_id is passed through to all scheduler methods (no tail filter)."""
        wallet = "0xabc"
        with mock.patch.object(
            temp_dbos_scheduler, "get_periodic_tasks", mock.AsyncMock(return_value=[])
        ) as mock_periodic, mock.patch.object(
            temp_dbos_scheduler, "get_pending_tasks", mock.AsyncMock(return_value=[])
        ) as mock_pending, mock.patch.object(
            temp_dbos_scheduler, "get_scheduled_tasks", mock.AsyncMock(return_value=[])
        ) as mock_scheduled, mock.patch.object(
            temp_dbos_scheduler, "get_results", mock.AsyncMock(return_value=[])
        ) as mock_results:
            await get_all_tasks(user_id=wallet)

        mock_periodic.assert_called_once_with(user_id=wallet)
        mock_pending.assert_called_once_with(user_id=wallet)
        mock_scheduled.assert_called_once_with(user_id=wallet)
        mock_results.assert_called_once_with(user_id=wallet)

    @pytest.mark.asyncio
    async def test_get_all_tasks_list_does_not_decrypt(self) -> None:
        """Test that the list path does not trigger any encryption/decryption."""
        result_executions = [
            Execution(id="cccccccc-cccc-cccc-cccc-cccccccccccc", status=TaskStatus.COMPLETED,
                      result="", result_metadata="")
        ]
        mock_scheduler = mock.Mock()
        mock_scheduler.get_periodic_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_pending_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_scheduled_tasks = mock.AsyncMock(return_value=[])
        mock_scheduler.get_results = mock.AsyncMock(return_value=result_executions)

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler), \
             mock.patch("octobot_node.scheduler.encryption.encrypt_task_result") as mock_crypto:
            tasks = await get_all_tasks()

        mock_crypto.assert_not_called()
        completed_exec = tasks[0].executions[0]
        assert completed_exec.result == ""
        assert completed_exec.result_metadata == ""


class TestGetTasksExportResults:
    """Tests for get_tasks_export_results function (batch decrypt-on-demand)."""

    @pytest.mark.asyncio
    async def test_decrypts_and_reencrypts_on_demand(self) -> None:
        """Crypto runs only when the export endpoint is called, once per task."""
        import dbos

        task_id_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        task_id_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        wallet = "0xowner"

        wf1 = _make_wf_status(task_id_1, dbos.WorkflowStatusString.SUCCESS.value, user_id=wallet)
        wf2 = _make_wf_status(task_id_2, dbos.WorkflowStatusString.SUCCESS.value, user_id=wallet)

        mock_instance = mock.AsyncMock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[wf1, wf2])

        fake_result = ("encrypted_result", "encrypted_metadata")

        async def fake_build(task_id, user_rsa):
            return {"result": fake_result[0], "result_metadata": fake_result[1]}

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock_instance
        mock_scheduler.get_workflows_export_results = mock.AsyncMock(
            return_value={
                task_id_1: {"result": fake_result[0], "result_metadata": fake_result[1]},
                task_id_2: {"result": fake_result[0], "result_metadata": fake_result[1]},
            }
        )

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_tasks_export_results([task_id_1, task_id_2], user_id=wallet)

        mock_scheduler.get_workflows_export_results.assert_called_once_with([task_id_1, task_id_2], wallet, user_rsa_public_key=None)
        assert task_id_1 in result
        assert task_id_2 in result
        assert result[task_id_1]["result"] == fake_result[0]

    @pytest.mark.asyncio
    async def test_empty_task_ids_returns_empty(self) -> None:
        """Empty task list returns empty dict without touching the scheduler."""
        mock_scheduler = mock.Mock()
        mock_scheduler.get_workflows_export_results = mock.AsyncMock()

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_tasks_export_results([], user_id="0xwallet")

        assert result == {}
        mock_scheduler.get_workflows_export_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_other_wallet(self) -> None:
        """Forbidden task ID returns error entry; matching task still resolves."""
        import dbos

        my_task = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        other_task = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        my_wallet = "0xmine"
        other_wallet = "0xother"

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.AsyncMock()
        mock_scheduler.get_workflows_export_results = mock.AsyncMock(
            return_value={
                my_task: {"result": "enc", "result_metadata": "meta"},
                other_task: {"error": "forbidden"},
            }
        )

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_tasks_export_results([my_task, other_task], user_id=my_wallet)

        assert result[my_task]["result"] == "enc"
        assert result[other_task]["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_partial_failure_isolates(self) -> None:
        """One failing task does not prevent other tasks from resolving."""
        import dbos

        good_task = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        bad_task = "cccccccc-cccc-cccc-cccc-cccccccccccc"

        mock_scheduler = mock.Mock()
        mock_scheduler.INSTANCE = mock.AsyncMock()
        mock_scheduler.get_workflows_export_results = mock.AsyncMock(
            return_value={
                good_task: {"result": "enc", "result_metadata": "meta"},
                bad_task: {"error": "not found"},
            }
        )

        with mock.patch("octobot_node.scheduler.SCHEDULER", mock_scheduler):
            result = await get_tasks_export_results([good_task, bad_task], user_id=None)

        assert result[good_task]["result"] == "enc"
        assert "error" in result[bad_task]


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
