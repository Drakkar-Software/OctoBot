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


def init_scheduler(db_file_name: str):
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
        if octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE is None:
            octobot_node.scheduler.SCHEDULER.create_queues()
        dbos.DBOS(config=config)
        octobot_node.scheduler.SCHEDULER.INSTANCE = dbos.DBOS
        octobot_node.scheduler.workflows.register_workflows()
    return dbos.DBOS


@pytest.fixture()
def temp_dbos_scheduler():
    # from https://docs.dbos.dev/python/tutorials/testing
    # don't use too muck as it is very slow
    with tempfile.NamedTemporaryFile() as temp_file:
        dbos_runtime = init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos_runtime.destroy()


def init_and_destroy_scheduler(db_file_name: str):
    dbos = init_scheduler(db_file_name)
    dbos.reset_system_database()
    dbos.launch()
    dbos.destroy()
