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
import logging

import dbos
import sqlalchemy

import octobot_node.config
import octobot_node.constants

_DBOS_SYSTEM_SCHEMA = "dbos"
_PENDING_WORKFLOW_STATUSES = (
    dbos.WorkflowStatusString.ENQUEUED.value,
    dbos.WorkflowStatusString.PENDING.value,
)


def _resolve_system_database_url() -> str:
    postgres_url = octobot_node.config.settings.SCHEDULER_POSTGRES_URL
    if postgres_url:
        return str(postgres_url)
    return f"sqlite:///{octobot_node.config.settings.SCHEDULER_SQLITE_FILE}"


def _workflow_status_table_reference(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        return "workflow_status"
    return f'"{_DBOS_SYSTEM_SCHEMA}"."workflow_status"'


def _workflow_status_table_exists(
    connection: sqlalchemy.Connection,
    *,
    database_url: str,
) -> bool:
    inspector = sqlalchemy.inspect(connection)
    if database_url.startswith("sqlite"):
        return inspector.has_table("workflow_status")
    return inspector.has_table("workflow_status", schema=_DBOS_SYSTEM_SCHEMA)


def migrate_stranded_workflow_versions(
    *,
    target_version: str | None = None,
) -> int:
    """
    Re-tag ENQUEUED/PENDING workflows to ``target_version`` before DBOS launch.

    OctoBot releases used to set DBOS ``application_version`` to the OctoBot
    version string, which stranded in-flight workflows after upgrades. This
    migration retags them to the stable scheduler application version.
    """
    resolved_target_version = target_version or octobot_node.constants.SCHEDULER_APPLICATION_VERSION
    database_url = _resolve_system_database_url()
    workflow_status_table = _workflow_status_table_reference(database_url)
    logger = logging.getLogger(__name__)

    engine = sqlalchemy.create_engine(database_url)
    try:
        with engine.begin() as connection:
            if not _workflow_status_table_exists(connection, database_url=database_url):
                logger.info(
                    "Skipping DBOS workflow version migration: workflow_status table not found"
                )
                return 0

            status_placeholders = ", ".join(
                f":status_{status_index}"
                for status_index in range(len(_PENDING_WORKFLOW_STATUSES))
            )
            status_parameters = {
                f"status_{status_index}": status_value
                for status_index, status_value in enumerate(_PENDING_WORKFLOW_STATUSES)
            }
            select_previous_versions_query = sqlalchemy.text(
                f"""
                SELECT DISTINCT application_version
                FROM {workflow_status_table}
                WHERE status IN ({status_placeholders})
                  AND (
                    application_version IS NULL
                    OR application_version != :target_version
                  )
                """
            )
            previous_version_rows = connection.execute(
                select_previous_versions_query,
                {
                    **status_parameters,
                    "target_version": resolved_target_version,
                },
            ).fetchall()
            previous_versions = [
                row[0] if row[0] is not None else "<null>"
                for row in previous_version_rows
            ]

            update_query = sqlalchemy.text(
                f"""
                UPDATE {workflow_status_table}
                SET application_version = :target_version
                WHERE status IN ({status_placeholders})
                  AND (
                    application_version IS NULL
                    OR application_version != :target_version
                  )
                """
            )
            update_result = connection.execute(
                update_query,
                {
                    **status_parameters,
                    "target_version": resolved_target_version,
                },
            )
            updated_count = update_result.rowcount or 0
    except Exception as error:
        raise RuntimeError(
            "Failed to migrate stranded DBOS workflow application versions "
            f"to {resolved_target_version!r}: {error}"
        ) from error
    finally:
        engine.dispose()

    if updated_count:
        logger.info(
            "Migrated %s stranded DBOS workflow(s) to application version %s "
            "(previous versions: %s)",
            updated_count,
            resolved_target_version,
            ", ".join(previous_versions) if previous_versions else "none",
        )
    else:
        logger.info(
            "No stranded DBOS workflows needed application version migration "
            "(target version: %s)",
            resolved_target_version,
        )
    return updated_count
