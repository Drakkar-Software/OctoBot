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

import octobot.community.node_journal.recording.accounts as accounts_module
import octobot.community.node_journal.recording.automations as automations_module
import octobot.community.node_journal.recording.process as process_module
import octobot.community.node_journal.recording.strategies as strategies_module
import octobot.community.node_journal.recording.sync as sync_module
import octobot.community.node_journal.recording.user_actions as user_actions_module
import octobot.community.node_journal.recording.wallet as wallet_module

record_account_auth_create_succeeded = accounts_module.record_account_auth_create_succeeded
record_account_auth_deleted = accounts_module.record_account_auth_deleted
record_account_deleted = accounts_module.record_account_deleted
record_account_edit_succeeded = accounts_module.record_account_edit_succeeded
record_account_validated = accounts_module.record_account_validated
record_account_validated_from_account = accounts_module.record_account_validated_from_account
record_account_validation_failed = accounts_module.record_account_validation_failed
record_accounts_refreshed = accounts_module.record_accounts_refreshed

record_automation_restarted = automations_module.record_automation_restarted
record_automation_run_errored = automations_module.record_automation_run_errored
record_automation_started = automations_module.record_automation_started
record_automation_stopped = automations_module.record_automation_stopped
record_first_automation_started = automations_module.record_first_automation_started
record_new_automation_created = automations_module.record_new_automation_created
record_new_automation_created_from_strategy = automations_module.record_new_automation_created_from_strategy

record_existing_config_detected = process_module.record_existing_config_detected
record_process_startup_failed = process_module.record_process_startup_failed
record_process_startup_succeeded = process_module.record_process_startup_succeeded
record_reconcile_completed = process_module.record_reconcile_completed
record_scheduler_init_failed = process_module.record_scheduler_init_failed

record_strategy_create_succeeded = strategies_module.record_strategy_create_succeeded
record_strategy_edit_succeeded = strategies_module.record_strategy_edit_succeeded

on_user_data_pull_succeeded = sync_module.on_user_data_pull_succeeded
record_sync_read_failed = sync_module.record_sync_read_failed
record_sync_storage_event = sync_module.record_sync_storage_event
reset_sync_tracker_after_node_startup = sync_module.reset_sync_tracker_after_node_startup

record_executor_failure = user_actions_module.record_executor_failure
record_external_action_failed = user_actions_module.record_external_action_failed
record_external_action_received = user_actions_module.record_external_action_received

record_wallet_operation_failed = wallet_module.record_wallet_operation_failed
record_wallet_setup_attempt = wallet_module.record_wallet_setup_attempt
record_wallet_setup_failed = wallet_module.record_wallet_setup_failed
record_wallet_setup_succeeded = wallet_module.record_wallet_setup_succeeded

__all__ = [
    "on_user_data_pull_succeeded",
    "record_account_auth_create_succeeded",
    "record_account_auth_deleted",
    "record_account_deleted",
    "record_account_edit_succeeded",
    "record_account_validated",
    "record_account_validated_from_account",
    "record_account_validation_failed",
    "record_accounts_refreshed",
    "record_automation_restarted",
    "record_automation_run_errored",
    "record_automation_started",
    "record_automation_stopped",
    "record_executor_failure",
    "record_existing_config_detected",
    "record_external_action_failed",
    "record_external_action_received",
    "record_first_automation_started",
    "record_new_automation_created",
    "record_new_automation_created_from_strategy",
    "record_process_startup_failed",
    "record_process_startup_succeeded",
    "record_reconcile_completed",
    "record_scheduler_init_failed",
    "record_strategy_create_succeeded",
    "record_strategy_edit_succeeded",
    "record_sync_read_failed",
    "record_sync_storage_event",
    "record_wallet_operation_failed",
    "record_wallet_setup_attempt",
    "record_wallet_setup_failed",
    "record_wallet_setup_succeeded",
    "reset_sync_tracker_after_node_startup",
]
