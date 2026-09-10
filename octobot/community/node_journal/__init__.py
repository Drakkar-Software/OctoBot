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

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.journey_summary as journey_summary_module
import octobot.community.node_journal.recording as journal_recording
import octobot.community.node_journal.sanitize as journal_sanitize
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store
import octobot.community.node_journal.sync_session as sync_session_module

is_journal_enabled = journal_module.is_journal_enabled
record = journal_module.record
record_failure = journal_module.record_failure
read_events = journal_module.read_events
initialize_for_config = journal_module.initialize_for_config
build_journey_summary = journey_summary_module.build_journey_summary
build_upload_envelope = journey_summary_module.build_upload_envelope
sanitize_error_message = journal_sanitize.sanitize_error_message
NodeJournalEvent = journal_events.NodeJournalEvent
UI_JOURNAL_EVENTS = journal_events.UI_JOURNAL_EVENTS

record_process_startup_succeeded = journal_recording.record_process_startup_succeeded
record_process_startup_failed = journal_recording.record_process_startup_failed
record_wallet_setup_attempt = journal_recording.record_wallet_setup_attempt
record_wallet_setup_succeeded = journal_recording.record_wallet_setup_succeeded
record_wallet_setup_failed = journal_recording.record_wallet_setup_failed
record_wallet_operation_failed = journal_recording.record_wallet_operation_failed
record_sync_read_failed = journal_recording.record_sync_read_failed
record_external_action_received = journal_recording.record_external_action_received
record_external_action_failed = journal_recording.record_external_action_failed
record_executor_failure = journal_recording.record_executor_failure
record_account_auth_create_succeeded = journal_recording.record_account_auth_create_succeeded
record_account_auth_deleted = journal_recording.record_account_auth_deleted
record_account_deleted = journal_recording.record_account_deleted
record_account_edit_succeeded = journal_recording.record_account_edit_succeeded
record_account_validated = journal_recording.record_account_validated
record_account_validated_from_account = journal_recording.record_account_validated_from_account
record_account_validation_failed = journal_recording.record_account_validation_failed
record_accounts_refreshed = journal_recording.record_accounts_refreshed
record_automation_edit_succeeded = journal_recording.record_automation_edit_succeeded
record_automation_restarted = journal_recording.record_automation_restarted
record_automation_stopped = journal_recording.record_automation_stopped
record_first_automation_started = journal_recording.record_first_automation_started
record_automation_started = journal_recording.record_automation_started
record_new_automation_created = journal_recording.record_new_automation_created
record_new_automation_created_from_strategy = journal_recording.record_new_automation_created_from_strategy
record_strategy_create_succeeded = journal_recording.record_strategy_create_succeeded
record_strategy_edit_succeeded = journal_recording.record_strategy_edit_succeeded
record_existing_config_detected = journal_recording.record_existing_config_detected
record_reconcile_completed = journal_recording.record_reconcile_completed
record_scheduler_init_failed = journal_recording.record_scheduler_init_failed
record_sync_storage_event = journal_recording.record_sync_storage_event
record_automation_run_errored = journal_recording.record_automation_run_errored
on_user_data_pull_succeeded = sync_session_module.on_user_data_pull_succeeded
reset_sync_tracker_after_node_startup = sync_session_module.reset_sync_tracker_after_node_startup

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
    "sanitize_error_message",
]
