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
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
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
        attributes = {
            "collection": collection,
            "sync_session_id": str(uuid.uuid4()),
            "connection_sequence": persisted_state.connection_sequence,
            "is_reconnect": not is_first_ever,
            "duration_since_install_start": _duration_since_install_start(now),
        }
        if prior_gap_seconds is not None:
            attributes["prior_gap_seconds"] = prior_gap_seconds
        journal_module.record(
            journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
            attributes=attributes,
        )
    persisted_state.last_user_data_pull_at = now
    journal_state.save_persisted_state(persisted_state)
    _tracker_reset_after_startup = False


def _duration_since_install_start(now: float) -> float | None:
    persisted_state = journal_state.load_persisted_state()
    if persisted_state.onboarding_started_at is None:
        return None
    return round(max(0.0, now - persisted_state.onboarding_started_at), 3)
