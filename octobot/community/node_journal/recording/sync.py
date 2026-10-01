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

import time
import uuid

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.recording._utils as recording_utils
import octobot.community.node_journal.state as journal_state


_tracker_reset_after_startup = False


def reset_sync_tracker_after_node_startup() -> None:
    global _tracker_reset_after_startup
    _tracker_reset_after_startup = True


def on_user_data_pull_succeeded(*, sync_user_id: str, collection: str) -> None:
    global _tracker_reset_after_startup
    if collection != "user-data":
        return
    now = time.time()
    persisted_state = journal_state.load_persisted_state()
    is_first_ever = persisted_state.last_user_data_pull_at is None
    prior_gap_seconds = None
    is_reconnect = False
    if _tracker_reset_after_startup and not is_first_ever:
        is_reconnect = True
        prior_gap_seconds = round(now - persisted_state.last_user_data_pull_at, 3)
    elif persisted_state.last_user_data_pull_at is not None:
        gap_seconds = now - persisted_state.last_user_data_pull_at
        if gap_seconds > journal_constants.SYNC_SESSION_GAP_SECONDS:
            is_reconnect = True
            prior_gap_seconds = round(gap_seconds, 3)
    if is_first_ever or is_reconnect or _tracker_reset_after_startup:
        persisted_state.connection_sequence += 1
        attributes = journal_models.JournalEventAttributes(
            collection=collection,
            sync_session_id=str(uuid.uuid4()),
            connection_sequence=persisted_state.connection_sequence,
            is_reconnect=not is_first_ever,
            duration_since_install_start=journal_state.duration_since_install_start(now),
            prior_gap_seconds=prior_gap_seconds,
        )
        journal_module.record(
            journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
            attributes=attributes,
        )
    persisted_state.last_user_data_pull_at = now
    journal_state.save_persisted_state(persisted_state)
    _tracker_reset_after_startup = False


def record_sync_read_failed(
    *,
    collection: str,
    failure_reason: journal_enums.SyncReadFailureReason,
    error: BaseException | None = None,
    error_message: str | None = None,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.SYNC_READ_FAILED,
        error=error,
        error_message=error_message,
        attributes=journal_models.JournalEventAttributes(
            collection=collection,
            failure_reason=recording_utils.enum_value(failure_reason),
        ),
    )


def record_sync_storage_event(
    event: journal_events.NodeJournalEvent,
    *,
    collection: str,
    provider: journal_enums.SyncStorageProvider,
    error: BaseException | None = None,
    recovery_action: journal_enums.SyncStorageRecoveryAction | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        collection=collection,
        provider=recording_utils.enum_value(provider),
        recovery_action=recording_utils.enum_value(recovery_action) if recovery_action is not None else None,
    )
    if error is None:
        journal_module.record(event, attributes=attributes)
        return
    journal_module.record_failure(event, error=error, attributes=attributes)
