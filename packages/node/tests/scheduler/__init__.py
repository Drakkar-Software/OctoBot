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
import asyncio
import pytest
import dbos
import mock
import tempfile

import octobot_node.constants as octobot_node_constants_module
import octobot_node.scheduler
import octobot_node.scheduler.workflows


class AutomationWorkflowIterationRetryInterval:
    """
    DBOS captures ``interval_seconds`` when ``AutomationWorkflow.execute_iteration`` is decorated.

    Tests call ``init_scheduler`` / ``temp_dbos_scheduler``, which temporarily replaces
    ``octobot_node.constants.AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS`` with this proxy so
    retry backoff reads a patchable value.

    While the attribute is ``self``, use ``baseline_seconds`` (snapshot taken before the patch).
    After nested ``mock.patch.object(..., AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS, float)``,
    multiplication uses ``float(v)``.

    If ``automation_workflow`` was imported before ``init_scheduler`` in this pytest worker,
    the step was already decorated with a plain float and nested patches do not change backoff.
    """

    def __init__(self, baseline_seconds: float):
        self._baseline_seconds = baseline_seconds

    def _effective_seconds(self) -> float:
        attribute_value = octobot_node_constants_module.AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS
        if attribute_value is self:
            return self._baseline_seconds
        return float(attribute_value)

    def __mul__(self, backoff_factor: float) -> float:
        return self._effective_seconds() * backoff_factor

    def __rmul__(self, backoff_factor: float) -> float:
        return self._effective_seconds() * backoff_factor

    def __float__(self) -> float:
        return float(self._effective_seconds())


def _reset_asyncio_default_executor() -> None:
    # DBOS async APIs call loop.set_default_executor(dbos._executor) on first use.
    # destroy_launched_dbos() shuts down that executor but leaves the loop pointing at it,
    # so later tests on the same pytest-xdist worker see "System database accessed before
    # DBOS was launched". Clear the binding so the next test gets a fresh default pool.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
    if loop.is_closed():
        return
    # Python 3.13 rejects None in set_default_executor(); assign directly so asyncio
    # lazily creates a fresh ThreadPoolExecutor on the next run_in_executor call.
    loop._default_executor = None


def _ensure_scheduler_queues() -> None:
    # destroy_launched_dbos() clears Scheduler queue handles; when destroy_registry=False
    # the global registry still owns the Queue declarations and re-creating them fails.
    scheduler = octobot_node.scheduler.SCHEDULER
    if scheduler.AUTOMATION_WORKFLOW_QUEUE is not None:
        return
    import dbos._dbos as dbos_internals
    import octobot_node.enums as octobot_node_enums_module
    registry = dbos_internals._get_or_create_dbos_registry()
    queue_bindings = {
        octobot_node_enums_module.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value: "AUTOMATION_WORKFLOW_QUEUE",
        octobot_node_enums_module.SchedulerQueues.USER_ACTION_QUEUE.value: "USER_ACTION_QUEUE",
        octobot_node_enums_module.SchedulerQueues.DBOS_CLEANUP_QUEUE.value: "DBOS_CLEANUP_QUEUE",
    }
    if all(queue_name in registry.queue_info_map for queue_name in queue_bindings):
        for queue_name, scheduler_attribute in queue_bindings.items():
            setattr(scheduler, scheduler_attribute, registry.queue_info_map[queue_name])
        return
    scheduler.create_queues()


def destroy_launched_dbos(*, destroy_registry: bool = False) -> None:
    """
    Tear down the DBOS singleton so the next test can reset the system database.

    Required when a previous test failed after ``launch()`` or when pytest-xdist
    runs many scheduler tests on the same worker.
    """
    # Clear executor binding before DBOS.destroy — see _reset_asyncio_default_executor.
    _reset_asyncio_default_executor()
    # destroy_registry=False keeps @DBOS.workflow decorators on the same registry; DBOS()
    # rebinds registry.dbos on the next launch.
    dbos.DBOS.destroy(workflow_completion_timeout_sec=0, destroy_registry=destroy_registry)
    octobot_node.scheduler.SCHEDULER.INSTANCE = None
    octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE = None
    octobot_node.scheduler.SCHEDULER.USER_ACTION_QUEUE = None
    octobot_node.scheduler.SCHEDULER.DBOS_CLEANUP_QUEUE = None


def init_scheduler(db_file_name: str, application_version: str | None = None):
    destroy_launched_dbos()
    baseline_seconds = float(octobot_node_constants_module.AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS)
    retry_interval_proxy = AutomationWorkflowIterationRetryInterval(baseline_seconds)
    with mock.patch.object(
        octobot_node_constants_module,
        "AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS",
        retry_interval_proxy,
    ):
        config: dbos.DBOSConfig = {
            "name": "scheduler_test",
            "system_database_url": f"sqlite:///{db_file_name}",
        }
        if application_version is not None:
            config["application_version"] = application_version
        _ensure_scheduler_queues()
        dbos.DBOS(config=config)
        octobot_node.scheduler.SCHEDULER.INSTANCE = dbos.DBOS
        octobot_node.scheduler.workflows.register_workflows()
    return dbos.DBOS


def init_scheduler_with_app_version(db_file_name: str, application_version: str):
    return init_scheduler(db_file_name, application_version=application_version)


@pytest.fixture()
def temp_dbos_scheduler():
    # from https://docs.dbos.dev/python/tutorials/testing
    # don't use too muck as it is very slow
    with tempfile.NamedTemporaryFile() as temp_file:
        destroy_launched_dbos()
        dbos_runtime = init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            destroy_launched_dbos()


def init_and_destroy_scheduler(db_file_name: str):
    destroy_launched_dbos()
    dbos_runtime = init_scheduler(db_file_name)
    dbos_runtime.reset_system_database()
    dbos_runtime.launch()
    destroy_launched_dbos()
