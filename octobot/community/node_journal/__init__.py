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

import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store

from octobot.community.node_journal.events import (
    NodeJournalEvent,
    UI_JOURNAL_EVENTS,
)
from octobot.community.node_journal.journal import (
    initialize_for_config,
    is_journal_enabled,
    read_events,
    record,
    record_failure,
)
from octobot.community.node_journal.journey_summary import (
    build_journey_summary,
    build_upload_envelope,
)
from octobot.community.node_journal.recording import (
    record_account_auth_create_succeeded,
    record_account_auth_deleted,
    record_account_deleted,
    record_account_edit_succeeded,
    record_account_validated,
    record_account_validated_from_account,
    record_account_validation_failed,
    record_accounts_refreshed,
    record_automation_edit_succeeded,
    record_automation_restarted,
    record_automation_run_errored,
    record_automation_started,
    record_automation_stopped,
    record_executor_failure,
    record_existing_config_detected,
    record_external_action_failed,
    record_external_action_received,
    record_first_automation_started,
    record_new_automation_created,
    record_new_automation_created_from_strategy,
    record_process_startup_failed,
    record_process_startup_succeeded,
    record_reconcile_completed,
    record_scheduler_init_failed,
    record_strategy_create_succeeded,
    record_strategy_edit_succeeded,
    record_sync_read_failed,
    record_sync_storage_event,
    record_wallet_operation_failed,
    record_wallet_setup_attempt,
    record_wallet_setup_failed,
    record_wallet_setup_succeeded,
)
from octobot.community.node_journal.sync_session import (
    on_user_data_pull_succeeded,
    reset_sync_tracker_after_node_startup,
)

__all__ = [
    "NodeJournalEvent",
    "UI_JOURNAL_EVENTS",
    "build_journey_summary",
    "build_upload_envelope",
    "initialize_for_config",
    "is_journal_enabled",
    "journal_state",
    "journal_store",
    "on_user_data_pull_succeeded",
    "read_events",
    "record",
    "record_account_auth_create_succeeded",
    "record_account_auth_deleted",
    "record_account_deleted",
    "record_account_edit_succeeded",
    "record_account_validated",
    "record_account_validated_from_account",
    "record_account_validation_failed",
    "record_accounts_refreshed",
    "record_automation_edit_succeeded",
    "record_automation_restarted",
    "record_automation_run_errored",
    "record_automation_started",
    "record_automation_stopped",
    "record_executor_failure",
    "record_existing_config_detected",
    "record_external_action_failed",
    "record_external_action_received",
    "record_failure",
    "record_first_automation_started",
    "record_new_automation_created",
    "record_new_automation_created_from_strategy",
    "record_strategy_create_succeeded",
    "record_strategy_edit_succeeded",
    "record_process_startup_failed",
    "record_process_startup_succeeded",
    "record_reconcile_completed",
    "record_scheduler_init_failed",
    "record_sync_read_failed",
    "record_sync_storage_event",
    "record_wallet_operation_failed",
    "record_wallet_setup_attempt",
    "record_wallet_setup_failed",
    "record_wallet_setup_succeeded",
    "reset_sync_tracker_after_node_startup",
]
