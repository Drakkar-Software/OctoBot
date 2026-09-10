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

import logging

import octobot_node.config
import octobot_node.constants
import octobot_node.scheduler.scheduler as scheduler_lib
import octobot_node.scheduler.workflows
import octobot_node.scheduler.workflows_version_migration as workflows_version_migration

import octobot.community.node_journal as node_journal

scheduler_logger = logging.getLogger(__name__)

SCHEDULER: scheduler_lib.Scheduler = scheduler_lib.Scheduler()

_shutdown_done = False
_scheduler_init_failure_recorded = False


def scheduler_init_failure_was_recorded() -> bool:
    return _scheduler_init_failure_recorded


def _record_scheduler_init_failed(**kwargs) -> None:
    global _scheduler_init_failure_recorded
    _scheduler_init_failure_recorded = True
    node_journal.record_scheduler_init_failed(**kwargs)


def is_enabled() -> bool:
    return SCHEDULER.is_enabled()


def is_initialized() -> bool:
    return SCHEDULER.is_initialized()


def _scheduler_backend() -> str:
    if octobot_node.config.settings.SCHEDULER_POSTGRES_URL:
        return "postgres"
    return "sqlite"


async def initialize_scheduler():
    global _shutdown_done, _scheduler_init_failure_recorded
    _shutdown_done = False
    _scheduler_init_failure_recorded = False
    scheduler_logger.info("Initializing scheduler")
    backend = _scheduler_backend()
    try:
        SCHEDULER.create()
    except Exception as exc:
        _record_scheduler_init_failed(
            init_phase="dbos_create",
            backend=backend,
            error=exc,
        )
        raise
    try:
        octobot_node.scheduler.workflows.register_workflows()
    except Exception as exc:
        _record_scheduler_init_failed(
            init_phase="register_workflows",
            backend=backend,
            error=exc,
        )
        raise
    if octobot_node.constants.ALWAYS_ENSURE_SCHEDULER_APPLICATION_VERSION:
        try:
            workflows_version_migration.migrate_stranded_workflow_versions(
                target_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
            )
        except Exception as exc:
            _record_scheduler_init_failed(
                init_phase="version_migration",
                backend=backend,
                error=exc,
            )
            raise
    import octobot_node.scheduler.schedules as schedules
    try:
        SCHEDULER.start()
    except Exception as exc:
        _record_scheduler_init_failed(
            init_phase="dbos_launch",
            backend=backend,
            error=exc,
        )
        raise
    # apply_schedules requires DBOS launch (sys_db); must run after start().
    try:
        await schedules.register_schedules(SCHEDULER)
    except Exception as exc:
        _record_scheduler_init_failed(
            init_phase="register_schedules",
            backend=backend,
            error=exc,
        )
        raise


async def shutdown_scheduler_and_trading_signal_channel() -> None:
    global _shutdown_done
    if _shutdown_done or not is_initialized():
        return
    try:
        import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
        await trading_signals_channel.shutdown_internal_trading_signal_channel()
    except ImportError:
        pass
    SCHEDULER.stop()
    _shutdown_done = True
