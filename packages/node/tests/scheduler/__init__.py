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
import tempfile

import octobot_node.scheduler
import octobot_node.scheduler.workflows


def init_scheduler(db_file_name: str):
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
        dbos =init_scheduler(temp_file.name)
        dbos.reset_system_database()
        dbos.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos.destroy()


def init_and_destroy_scheduler(db_file_name: str):
    dbos = init_scheduler(db_file_name)
    dbos.reset_system_database()
    dbos.launch()
    dbos.destroy()
