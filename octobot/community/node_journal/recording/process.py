#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.recording._utils as recording_utils
import octobot.community.node_journal.recording.sync as sync_module
import octobot.community.node_journal.state as journal_state


def record_process_startup_succeeded(
    *,
    wallet_configured: bool,
    new_install: bool,
    reconciled: bool,
) -> None:
    sync_module.reset_sync_tracker_after_node_startup()
    journal_module.record(
        journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            wallet_configured=wallet_configured,
            new_install=new_install,
            reconciled=reconciled,
            duration_since_install_start=journal_state.duration_since_install_start(),
        ),
    )


def record_process_startup_failed(
    *,
    startup_phase: journal_enums.JournalStartupPhase,
    error: BaseException,
    force_exit: bool,
    wallet_configured: bool | None = None,
    new_install: bool | None = None,
    reconciled: bool | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        startup_phase=recording_utils.enum_value(startup_phase),
        force_exit=force_exit,
    )
    if wallet_configured is not None:
        attributes.wallet_configured = wallet_configured
    if new_install is not None:
        attributes.new_install = new_install
    if reconciled is not None:
        attributes.reconciled = reconciled
    journal_module.record_failure(
        journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED,
        error=error,
        attributes=attributes,
    )


def record_existing_config_detected(
    *,
    wallet_configured: bool,
    account_count: int,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.EXISTING_CONFIG_DETECTED,
        attributes=journal_models.JournalEventAttributes(
            wallet_configured=wallet_configured,
            account_count=account_count,
        ),
    )


def record_reconcile_completed(
    *,
    automation_count: int,
    running_automation_count: int,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.RECONCILE_COMPLETED,
        attributes=journal_models.JournalEventAttributes(
            automation_count=automation_count,
            running_automation_count=running_automation_count,
        ),
    )


def record_scheduler_init_failed(
    *,
    init_phase: journal_enums.JournalInitPhase,
    backend: journal_enums.JournalSchedulerBackend,
    error: BaseException,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.SCHEDULER_INIT_FAILED,
        error=error,
        attributes=journal_models.JournalEventAttributes(
            init_phase=recording_utils.enum_value(init_phase),
            backend=recording_utils.enum_value(backend),
        ),
    )
