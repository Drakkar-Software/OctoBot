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

import enum


class NodeJournalEvent(enum.StrEnum):
    NODE_PROCESS_STARTUP_SUCCEEDED = "node_process_startup_succeeded"
    NODE_PROCESS_STARTUP_FAILED = "node_process_startup_failed"
    NODE_PROCESS_STOP = "node_process_stop"
    WALLET_SETUP_ATTEMPT = "wallet_setup_attempt"
    WALLET_SETUP_SUCCEEDED = "wallet_setup_succeeded"
    WALLET_SETUP_FAILED = "wallet_setup_failed"
    WALLET_OPERATION_FAILED = "wallet_operation_failed"
    EXTERNAL_INTERFACE_CONNECTED = "external_interface_connected"
    SYNC_READ_FAILED = "sync_read_failed"
    EXTERNAL_ACTION_RECEIVED = "external_action_received"
    EXTERNAL_ACTION_FAILED = "external_action_failed"
    ACCOUNT_AUTH_CREATE_ATTEMPT = "account_auth_create_attempt"
    ACCOUNT_AUTH_CREATE_SUCCEEDED = "account_auth_create_succeeded"
    ACCOUNT_AUTH_CREATE_FAILED = "account_auth_create_failed"
    ACCOUNT_CREATE_ATTEMPT = "account_create_attempt"
    ACCOUNT_VALIDATED = "account_validated"
    ACCOUNT_VALIDATION_FAILED = "account_validation_failed"
    ACCOUNT_EDIT_ATTEMPT = "account_edit_attempt"
    ACCOUNT_EDIT_SUCCEEDED = "account_edit_succeeded"
    ACCOUNT_EDIT_FAILED = "account_edit_failed"
    STRATEGY_CREATE_ATTEMPT = "strategy_create_attempt"
    STRATEGY_CREATE_SUCCEEDED = "strategy_create_succeeded"
    STRATEGY_CREATE_FAILED = "strategy_create_failed"
    STRATEGY_EDIT_ATTEMPT = "strategy_edit_attempt"
    STRATEGY_EDIT_SUCCEEDED = "strategy_edit_succeeded"
    STRATEGY_EDIT_FAILED = "strategy_edit_failed"
    AUTOMATION_CREATE_ATTEMPT = "automation_create_attempt"
    AUTOMATION_CREATE_FAILED = "automation_create_failed"
    FIRST_AUTOMATION_STARTED = "first_automation_started"
    AUTOMATION_EDIT_ATTEMPT = "automation_edit_attempt"
    AUTOMATION_EDIT_SUCCEEDED = "automation_edit_succeeded"
    AUTOMATION_EDIT_FAILED = "automation_edit_failed"
    AUTOMATION_STARTED = "automation_started"
    AUTOMATION_STOPPED = "automation_stopped"
    AUTOMATION_RESTARTED = "automation_restarted"
    AUTOMATION_RUN_ERRORED = "automation_run_errored"
    AUTOMATION_RUN_RECOVERED = "automation_run_recovered"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_AUTH_DELETED = "account_auth_deleted"
    ACCOUNTS_REFRESHED = "accounts_refreshed"
    EXISTING_CONFIG_DETECTED = "existing_config_detected"
    RECONCILE_COMPLETED = "reconcile_completed"
    UI_BOOT_FAILED = "ui_boot_failed"
    UI_SESSION_ABORTED = "ui_session_aborted"
    UI_AUTH_STATE_BROKEN = "ui_auth_state_broken"
    UI_FATAL_RENDER_ERROR = "ui_fatal_render_error"
    UI_CLIENT_STORAGE_RESET = "ui_client_storage_reset"
    SYNC_STORAGE_DECRYPT_FAILED = "sync_storage_decrypt_failed"
    SYNC_STORAGE_FORMAT_ERROR = "sync_storage_format_error"
    SYNC_STORAGE_SCHEMA_RECOVERY = "sync_storage_schema_recovery"
    SYNC_STORAGE_LOAD_FAILED = "sync_storage_load_failed"
    SCHEDULER_INIT_FAILED = "scheduler_init_failed"


UI_JOURNAL_EVENTS = frozenset({
    NodeJournalEvent.UI_BOOT_FAILED,
    NodeJournalEvent.UI_SESSION_ABORTED,
    NodeJournalEvent.UI_AUTH_STATE_BROKEN,
    NodeJournalEvent.UI_FATAL_RENDER_ERROR,
    NodeJournalEvent.UI_CLIENT_STORAGE_RESET,
})

FAILURE_EVENTS = frozenset(event for event in NodeJournalEvent if event.value.endswith("_failed") or event.value.endswith("_errored"))

FUNNEL_STEP_ORDER: tuple[NodeJournalEvent, ...] = (
    NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
    NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED,
    NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
    NodeJournalEvent.WALLET_SETUP_FAILED,
    NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
    NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED,
    NodeJournalEvent.ACCOUNT_AUTH_CREATE_FAILED,
    NodeJournalEvent.ACCOUNT_VALIDATED,
    NodeJournalEvent.ACCOUNT_VALIDATION_FAILED,
    NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
    NodeJournalEvent.STRATEGY_CREATE_FAILED,
    NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
    NodeJournalEvent.STRATEGY_EDIT_FAILED,
    NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
    NodeJournalEvent.AUTOMATION_CREATE_FAILED,
    NodeJournalEvent.FIRST_AUTOMATION_STARTED,
)

FUNNEL_STEP_RANK = {event: index for index, event in enumerate(FUNNEL_STEP_ORDER)}
