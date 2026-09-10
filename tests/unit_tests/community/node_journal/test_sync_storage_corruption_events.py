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

import octobot_sync.errors as sync_errors

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording


class TestRecordSyncStorageEvent:
    def test_records_decrypt_failed(self, journal_persisted_state):
        journal_recording.record_sync_storage_event(
            journal_events.NodeJournalEvent.SYNC_STORAGE_DECRYPT_FAILED,
            collection="user-accounts",
            provider="local",
            error=sync_errors.OctobotSyncCryptoDecryptError("bad key"),
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SYNC_STORAGE_DECRYPT_FAILED
        assert event_line.attributes.collection == "user-accounts"
        assert event_line.attributes.provider == "local"
        assert event_line.attributes.error_category == "OctobotSyncCryptoDecryptError"

    def test_records_format_error(self, journal_persisted_state):
        journal_recording.record_sync_storage_event(
            journal_events.NodeJournalEvent.SYNC_STORAGE_FORMAT_ERROR,
            collection="user-strategies",
            provider="local",
            error=ValueError("invalid json"),
        )
        events = journal_module.read_events()
        assert events[0].event == journal_events.NodeJournalEvent.SYNC_STORAGE_FORMAT_ERROR

    def test_records_schema_recovery_without_error(self, journal_persisted_state):
        journal_recording.record_sync_storage_event(
            journal_events.NodeJournalEvent.SYNC_STORAGE_SCHEMA_RECOVERY,
            collection="user-data",
            provider="local",
            recovery_action="drop_invalid_items",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SYNC_STORAGE_SCHEMA_RECOVERY
        assert event_line.attributes.recovery_action == "drop_invalid_items"
        assert event_line.attributes.error_category is None
