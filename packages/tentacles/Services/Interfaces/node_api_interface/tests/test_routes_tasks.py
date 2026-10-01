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

import datetime
from unittest.mock import AsyncMock, patch

import octobot_node.models

from .conftest import (
    ADMIN_ADDRESS,
    TENANT_ADDRESS,
    ADMIN_TASK_ID,
    TENANT_TASK_ID,
    ADMIN_USER_ID,
    TENANT_USER_ID,
)


def _admin_task() -> octobot_node.models.Task:
    return octobot_node.models.Task(id=ADMIN_TASK_ID, user_id=ADMIN_USER_ID)


def _tenant_task() -> octobot_node.models.Task:
    return octobot_node.models.Task(id=TENANT_TASK_ID, user_id=TENANT_USER_ID)


def test_admin_sees_all_tasks(admin_client, mock_auth):
    all_tasks = [_admin_task(), _tenant_task()]
    mock_get = AsyncMock(return_value=all_tasks)
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        resp = admin_client.get("/api/v1/tasks/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    # Admin passes no user_id filter
    mock_get.assert_called_once_with(user_id=None)


def test_tenant_sees_only_own_tasks(tenant_client, mock_auth):
    mock_get = AsyncMock(return_value=[_tenant_task()])
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        resp = tenant_client.get("/api/v1/tasks/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == TENANT_USER_ID
    # Tenant's user_id is passed as filter
    mock_get.assert_called_once_with(user_id=TENANT_USER_ID)


def test_task_creation_stamps_tenant_wallet(tenant_client, mock_auth):
    mock_trigger = AsyncMock(return_value=True)
    with patch("octobot_node.scheduler.tasks.trigger_task", new=mock_trigger):
        with patch("octobot_node.scheduler.is_initialized", return_value=True):
            resp = tenant_client.post("/api/v1/tasks/", json=[{"id": TENANT_TASK_ID}])
    assert resp.status_code == 200
    assert resp.json() == [1, 0]
    stamped_task = mock_trigger.call_args[0][0]
    assert stamped_task.user_id == TENANT_USER_ID


def test_task_creation_stamps_admin_wallet(admin_client, mock_auth):
    mock_trigger = AsyncMock(return_value=True)
    with patch("octobot_node.scheduler.tasks.trigger_task", new=mock_trigger):
        with patch("octobot_node.scheduler.is_initialized", return_value=True):
            resp = admin_client.post("/api/v1/tasks/", json=[{"id": ADMIN_TASK_ID}])
    assert resp.status_code == 200
    stamped_task = mock_trigger.call_args[0][0]
    assert stamped_task.user_id == ADMIN_USER_ID


def test_task_creation_counts_failures(tenant_client, mock_auth):
    mock_trigger = AsyncMock(return_value=False)
    with patch("octobot_node.scheduler.tasks.trigger_task", new=mock_trigger):
        with patch("octobot_node.scheduler.is_initialized", return_value=True):
            resp = tenant_client.post("/api/v1/tasks/", json=[{"id": TENANT_TASK_ID}])
    assert resp.status_code == 200
    assert resp.json() == [0, 1]


def test_admin_metrics_uses_no_filter(admin_client, mock_auth):
    mock_metrics = AsyncMock(return_value={"total": 10})
    with patch("octobot_node.scheduler.api.get_task_metrics", new=mock_metrics):
        resp = admin_client.get("/api/v1/tasks/metrics")
    assert resp.status_code == 200
    mock_metrics.assert_called_once_with(user_id=None)


def test_tenant_metrics_uses_wallet_filter(tenant_client, mock_auth):
    mock_metrics = AsyncMock(return_value={"total": 3})
    with patch("octobot_node.scheduler.api.get_task_metrics", new=mock_metrics):
        resp = tenant_client.get("/api/v1/tasks/metrics")
    assert resp.status_code == 200
    mock_metrics.assert_called_once_with(user_id=TENANT_USER_ID)


def test_admin_can_delete_any_task(admin_client, mock_auth):
    mock_delete = AsyncMock(return_value=[ADMIN_TASK_ID])
    with patch("octobot_node.scheduler.api.delete_tasks", new=mock_delete):
        resp = admin_client.delete(f"/api/v1/tasks/?taskIds={ADMIN_TASK_ID}")
    assert resp.status_code == 200
    mock_delete.assert_called_once_with([ADMIN_TASK_ID])


def test_tenant_can_delete_own_tasks(tenant_client, mock_auth):
    mock_get = AsyncMock(return_value=[_tenant_task()])
    mock_delete = AsyncMock(return_value=[TENANT_TASK_ID])
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        with patch("octobot_node.scheduler.api.delete_tasks", new=mock_delete):
            resp = tenant_client.delete(f"/api/v1/tasks/?taskIds={TENANT_TASK_ID}")
    assert resp.status_code == 200
    mock_delete.assert_called_once_with([TENANT_TASK_ID])


def test_tenant_cannot_delete_other_wallet_tasks(tenant_client, mock_auth):
    # Tenant owns only TENANT_TASK_ID; requesting ADMIN_TASK_ID must be 403
    mock_get = AsyncMock(return_value=[_tenant_task()])
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        resp = tenant_client.delete(f"/api/v1/tasks/?taskIds={ADMIN_TASK_ID}")
    assert resp.status_code == 403


def test_get_tasks_requires_auth(client, mock_auth):
    resp = client.get("/api/v1/tasks/")
    assert resp.status_code == 401


def test_post_tasks_requires_auth(client, mock_auth):
    resp = client.post("/api/v1/tasks/", json=[{"id": TENANT_TASK_ID}])
    assert resp.status_code == 401


def test_delete_tasks_requires_auth(client, mock_auth):
    resp = client.delete(f"/api/v1/tasks/?taskIds={TENANT_TASK_ID}")
    assert resp.status_code == 401


def _task_with_completed_at(task_id: str, completed_at: datetime.datetime) -> octobot_node.models.Task:
    return octobot_node.models.Task(
        id=task_id,
        executions=[
            octobot_node.models.Execution(
                id=task_id,
                status=octobot_node.models.TaskStatus.COMPLETED,
                completed_at=completed_at,
            )
        ],
    )


def test_get_tasks_sorts_newest_first_when_newest_is_last_in_storage_order(admin_client, mock_auth):
    oldest_id = "11111111-1111-1111-1111-111111111111"
    middle_id = "22222222-2222-2222-2222-222222222222"
    newest_id = "33333333-3333-3333-3333-333333333333"
    unsorted_tasks = [
        _task_with_completed_at(
            oldest_id,
            datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        ),
        _task_with_completed_at(
            middle_id,
            datetime.datetime(2024, 2, 1, tzinfo=datetime.timezone.utc),
        ),
        _task_with_completed_at(
            newest_id,
            datetime.datetime(2024, 3, 1, tzinfo=datetime.timezone.utc),
        ),
    ]
    mock_get = AsyncMock(return_value=unsorted_tasks)
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        resp = admin_client.get("/api/v1/tasks/?page=1&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["id"] == newest_id


def test_get_tasks_page_two_has_no_overlap_with_page_one(admin_client, mock_auth):
    task_ids = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "dddddddd-dddd-dddd-dddd-dddddddddddd",
    ]
    unsorted_tasks = [
        _task_with_completed_at(
            task_id,
            datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
            + datetime.timedelta(days=index),
        )
        for index, task_id in enumerate(task_ids)
    ]
    mock_get = AsyncMock(return_value=unsorted_tasks)
    with patch("octobot_node.scheduler.api.get_all_tasks", new=mock_get):
        page_one = admin_client.get("/api/v1/tasks/?page=1&limit=2")
        page_two = admin_client.get("/api/v1/tasks/?page=2&limit=2")
    assert page_one.status_code == 200
    assert page_two.status_code == 200
    page_one_ids = {row["id"] for row in page_one.json()}
    page_two_ids = {row["id"] for row in page_two.json()}
    assert page_one_ids.isdisjoint(page_two_ids)
    assert len(page_one_ids) == 2
    assert len(page_two_ids) == 2
