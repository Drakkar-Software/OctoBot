#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import tempfile
import time

import dbos
import mock
import pytest

import octobot_node.constants
import octobot_node.scheduler
import octobot_node.scheduler.workflows_version_migration as workflows_version_migration

import tests.scheduler as scheduler_test_util

_OLD_APPLICATION_VERSION = "3.0.0-beta0"
_TEST_QUEUE = dbos.Queue(name="version_migration_test_queue")
_WORKFLOW_SLEEP_SECONDS = 1.5


class TestMigrateStrandedWorkflowVersions:
    def test_returns_zero_when_workflow_status_table_missing(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            sqlite_path = f"{temp_directory}/empty.db"
            with mock.patch.object(
                workflows_version_migration.octobot_node.config.settings,
                "SCHEDULER_POSTGRES_URL",
                None,
            ), mock.patch.object(
                workflows_version_migration.octobot_node.config.settings,
                "SCHEDULER_SQLITE_FILE",
                sqlite_path,
            ):
                updated_count = workflows_version_migration.migrate_stranded_workflow_versions(
                    target_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                )

        assert updated_count == 0

    def test_retags_enqueued_workflows_to_target_version(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            scheduler_test_util.destroy_launched_dbos()
            scheduler_test_util.init_scheduler(
                temp_file.name,
                application_version=_OLD_APPLICATION_VERSION,
            )
            dbos.DBOS.reset_system_database()
            dbos.DBOS.launch()

            @octobot_node.scheduler.SCHEDULER.INSTANCE.workflow()
            async def stranded_workflow() -> str:
                return "done"

            workflow_handle = _TEST_QUEUE.enqueue(stranded_workflow)
            stranded_workflow_id = workflow_handle.get_workflow_id()

            octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            octobot_node.scheduler.SCHEDULER.INSTANCE = None

            with mock.patch.object(
                workflows_version_migration.octobot_node.config.settings,
                "SCHEDULER_POSTGRES_URL",
                None,
            ), mock.patch.object(
                workflows_version_migration.octobot_node.config.settings,
                "SCHEDULER_SQLITE_FILE",
                temp_file.name,
            ):
                updated_count = workflows_version_migration.migrate_stranded_workflow_versions(
                    target_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                )

            assert updated_count == 1

            scheduler_test_util.init_scheduler(
                temp_file.name,
                application_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
            )
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()

            migrated_status = dbos.DBOS.get_workflow_status(stranded_workflow_id)
            assert migrated_status is not None
            assert migrated_status.app_version == octobot_node.constants.SCHEDULER_APPLICATION_VERSION
            assert migrated_status.status == dbos.WorkflowStatusString.ENQUEUED.value

            scheduler_test_util.destroy_launched_dbos()


class TestStrandedWorkflowRecoveryAfterVersionMigration:
    @pytest.mark.asyncio
    async def test_stranded_workflows_resume_after_application_version_migration(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            try:
                scheduler_test_util.destroy_launched_dbos()
                scheduler_test_util.init_scheduler(
                    temp_file.name,
                    application_version=_OLD_APPLICATION_VERSION,
                )

                @octobot_node.scheduler.SCHEDULER.INSTANCE.workflow()
                async def sleeper_workflow() -> str:
                    await dbos.DBOS.sleep_async(_WORKFLOW_SLEEP_SECONDS)
                    return "recovered"

                dbos.DBOS.reset_system_database()
                dbos.DBOS.launch()
                await _TEST_QUEUE.enqueue_async(sleeper_workflow)

                enqueued_workflows = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                    status=[dbos.WorkflowStatusString.ENQUEUED.value],
                )
                assert len(enqueued_workflows) == 1
                stranded_workflow_id = enqueued_workflows[0].workflow_id

                octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
                octobot_node.scheduler.SCHEDULER.INSTANCE = None

                with mock.patch.object(
                    workflows_version_migration.octobot_node.config.settings,
                    "SCHEDULER_POSTGRES_URL",
                    None,
                ), mock.patch.object(
                    workflows_version_migration.octobot_node.config.settings,
                    "SCHEDULER_SQLITE_FILE",
                    temp_file.name,
                ):
                    workflows_version_migration.migrate_stranded_workflow_versions(
                        target_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                    )

                scheduler_test_util.init_scheduler(
                    temp_file.name,
                    application_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                )
                octobot_node.scheduler.SCHEDULER.INSTANCE.launch()

                recovery_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
                    stranded_workflow_id,
                )
                workflow_result = await recovery_handle.get_result()
                assert workflow_result == "recovered"

                final_status = await recovery_handle.get_status()
                assert final_status.status == dbos.WorkflowStatusString.SUCCESS.value
                assert final_status.app_version == octobot_node.constants.SCHEDULER_APPLICATION_VERSION
            finally:
                scheduler_test_util.destroy_launched_dbos()

    @pytest.mark.asyncio
    async def test_pending_workflow_recovers_after_version_migration(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            try:
                scheduler_test_util.destroy_launched_dbos()
                scheduler_test_util.init_scheduler(
                    temp_file.name,
                    application_version=_OLD_APPLICATION_VERSION,
                )

                @octobot_node.scheduler.SCHEDULER.INSTANCE.workflow()
                async def sleeper_workflow() -> str:
                    await dbos.DBOS.sleep_async(_WORKFLOW_SLEEP_SECONDS)
                    return "pending-recovered"

                dbos.DBOS.reset_system_database()
                dbos.DBOS.launch()
                await _TEST_QUEUE.enqueue_async(sleeper_workflow)

                pending_workflows = await octobot_node.scheduler.SCHEDULER.INSTANCE.list_workflows_async(
                    status=[
                        dbos.WorkflowStatusString.ENQUEUED.value,
                        dbos.WorkflowStatusString.PENDING.value,
                    ],
                )
                assert len(pending_workflows) == 1
                stranded_workflow_id = pending_workflows[0].workflow_id

                time.sleep(0.2)
                octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
                octobot_node.scheduler.SCHEDULER.INSTANCE = None

                with mock.patch.object(
                    workflows_version_migration.octobot_node.config.settings,
                    "SCHEDULER_POSTGRES_URL",
                    None,
                ), mock.patch.object(
                    workflows_version_migration.octobot_node.config.settings,
                    "SCHEDULER_SQLITE_FILE",
                    temp_file.name,
                ):
                    workflows_version_migration.migrate_stranded_workflow_versions(
                        target_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                    )

                scheduler_test_util.init_scheduler(
                    temp_file.name,
                    application_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
                )
                octobot_node.scheduler.SCHEDULER.INSTANCE.launch()

                recovery_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
                    stranded_workflow_id,
                )
                workflow_result = await recovery_handle.get_result()
                assert workflow_result == "pending-recovered"

                final_status = await recovery_handle.get_status()
                assert final_status.status == dbos.WorkflowStatusString.SUCCESS.value
                assert final_status.app_version == octobot_node.constants.SCHEDULER_APPLICATION_VERSION
            finally:
                scheduler_test_util.destroy_launched_dbos()
