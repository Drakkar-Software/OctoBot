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
import pytest
import tempfile
import dbos
import logging
import time

import octobot_node.scheduler

QUEUE = dbos.Queue(name="test_queue")

WF_TO_CREATE = 10
WF_SLEEP_TIME = 1.5 # note: reducing this value wont speed up the test

async def _init_dbos_scheduler(db_file_name: str, reset_database: bool = False):
    config: dbos.DBOSConfig = {
        "name": "scheduler_test",
        "system_database_url": f"sqlite:///{db_file_name}",
        "max_executor_threads": 2, # 2 is the minimum number of threads to let dbos recover properly with pending workflows
    }
    dbos.DBOS(config=config)
    if reset_database:
        dbos.DBOS.reset_system_database()
    octobot_node.scheduler.SCHEDULER.INSTANCE = dbos.DBOS


class TestSchedulerRecovery:

    @pytest.mark.asyncio
    async def test_recover_after_shutdown(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            await _init_dbos_scheduler(temp_file.name, reset_database=True)

            @octobot_node.scheduler.SCHEDULER.INSTANCE.dbos_class()
            class Sleeper():
                @staticmethod
                @octobot_node.scheduler.SCHEDULER.INSTANCE.workflow()
                async def sleeper_workflow(identifier: float) -> float:
                    logging.info(f"sleeper_workflow {identifier} started")
                    await dbos.DBOS.sleep_async(WF_SLEEP_TIME)
                    logging.info(f"sleeper_workflow {identifier} done")
                    return identifier
    
            logging.info(f"Launching DBOS instance 1 ...")
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()
            logging.info(f"DBOS instance 1 launched")

            # 1. simple execution
            t0 = time.time()
            for i in range(WF_TO_CREATE):
                await QUEUE.enqueue_async(Sleeper.sleeper_workflow, i)
            wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=["ENQUEUED", "PENDING"]
            )
            assert len(wfs) == WF_TO_CREATE
            results_part1: list[int] = []
            for wf_status in wfs:
                handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(wf_status.workflow_id)
                r = await handle.get_result()
                assert 0 <= r < WF_TO_CREATE
                results_part1.append(int(r))
            duration = time.time() - t0
            logging.info(f"Workflow batch completed in {duration} seconds")
            max_duration = WF_TO_CREATE * WF_SLEEP_TIME * 0.9 # 90% of the 1 by 1 time to ensure asynchronous execution. usually 3 to 4 seconds on a normal machine
            assert duration <= max_duration, f"Workflow batch part 1 completed in {duration} seconds, expected <= {max_duration}"
            assert sorted(results_part1) == list(range(WF_TO_CREATE))
            success_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.SUCCESS.value]
            )
            assert len(success_wfs) == WF_TO_CREATE

            # 2. enqueue 10 more and restart
            for i in range(WF_TO_CREATE):
                await QUEUE.enqueue_async(Sleeper.sleeper_workflow, i)
            logging.info(f"Destroying DBOS instance 1 ...")
            octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            logging.info(f"DBOS instance 1 destroyed")

            # 3. restart and check completed workflows
            logging.info(f"Launching DBOS instance 2 ...")
            await _init_dbos_scheduler(temp_file.name)
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()
            logging.info(f"DBOS instance 2 launched")
            all_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async()
            assert len(all_wfs) == WF_TO_CREATE * 2
            pending_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=["ENQUEUED", "PENDING"]
            )
            assert len(pending_wfs) == WF_TO_CREATE
            # enqueue a second batch of workflows
            for i in range(WF_TO_CREATE, WF_TO_CREATE*2):
                await QUEUE.enqueue_async(Sleeper.sleeper_workflow, i)
            # Only ENQUEUED/PENDING: part 1 workflows are already SUCCESS (same inputs 0..9)
            # and must not be awaited again or get_result would duplicate those ids here.
            wfs_to_finish = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
            )
            assert len(wfs_to_finish) == WF_TO_CREATE * 2
            t0 = time.time()
            results_part2: list[int] = []
            for wf_status in wfs_to_finish:
                handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(wf_status.workflow_id)
                r = await handle.get_result()
                assert 0 <= r < WF_TO_CREATE*2
                results_part2.append(int(r))
            duration = time.time() - t0
            logging.info(f"2 parallel workflow batches completed in {duration} seconds")
            max_duration = WF_TO_CREATE * WF_SLEEP_TIME * 2 * 0.9 # 90% of the 1 by 1 time to ensure asynchronous execution. usually 3 to 4 seconds on a normal machine
            assert duration < max_duration, f"Workflow batch part 2 completed in {duration} seconds, expected <= {max_duration}"
            assert sorted(results_part2) == list(range(WF_TO_CREATE*2))
            success_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.SUCCESS.value]
            )
            assert len(success_wfs) == WF_TO_CREATE * 3
            no_pending = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
            )
            assert no_pending == []
            logging.info(f"Destroying DBOS instance 2 ...")
            octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            logging.info(f"DBOS instance 2 destroyed")

            # 4. restart and check completed workflows
            logging.info(f"Launching DBOS instance 3 ...")
            await _init_dbos_scheduler(temp_file.name)
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()
            logging.info(f"DBOS instance 3 launched")
            # all 30 worflows are now historized
            pending_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                status=["ENQUEUED", "PENDING"]
            )
            assert pending_wfs == []
            all_wfs = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async()
            assert len(all_wfs) == WF_TO_CREATE * 3
            logging.info(f"Destroying DBOS instance 3 ...")
            octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            logging.info(f"DBOS instance 3 destroyed")

    