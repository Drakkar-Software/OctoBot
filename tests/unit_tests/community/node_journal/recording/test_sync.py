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

import mock

import octobot_sync.errors as sync_errors

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording
import octobot.community.node_journal.recording.sync as sync_module
import octobot.community.node_journal.state as journal_state


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


class TestResetSyncTrackerAfterNodeStartup:
    def test_sets_tracker_flag(self):
        sync_module.reset_sync_tracker_after_node_startup()
        assert sync_module._tracker_reset_after_startup is True


class TestOnUserDataPullSucceeded:
    def test_first_pull_records_external_interface_connected(self, journal_persisted_state):
        with mock.patch("octobot.community.node_journal.recording.sync.time.time", return_value=2_000.0):
            sync_module.on_user_data_pull_succeeded(sync_user_id="user-1", collection="user-data")

        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED
        assert event_line.attributes.collection == "user-data"
        assert event_line.attributes.connection_sequence == 1
        assert event_line.attributes.is_reconnect is False
        assert event_line.attributes.duration_since_install_start == 1_000.0

        persisted_state = journal_state.load_persisted_state()
        assert persisted_state.last_user_data_pull_at == 2_000.0
        assert sync_module._tracker_reset_after_startup is False

    def test_ignores_non_user_data_collection(self, journal_persisted_state):
        sync_module.on_user_data_pull_succeeded(sync_user_id="user-1", collection="user-accounts")
        assert journal_module.read_events() == []

    def test_second_pull_within_gap_does_not_record(self, journal_persisted_state):
        journal_persisted_state.last_user_data_pull_at = 1_000.0
        journal_persisted_state.connection_sequence = 1
        journal_state.save_persisted_state(journal_persisted_state)

        with mock.patch("octobot.community.node_journal.recording.sync.time.time", return_value=2_000.0):
            sync_module.on_user_data_pull_succeeded(sync_user_id="user-1", collection="user-data")

        assert journal_module.read_events() == []

    def test_pull_after_gap_records_reconnect_with_prior_gap(self, journal_persisted_state):
        journal_persisted_state.last_user_data_pull_at = 1_000.0
        journal_persisted_state.connection_sequence = 1
        journal_state.save_persisted_state(journal_persisted_state)

        reconnect_timestamp = 1_000.0 + journal_constants.SYNC_SESSION_GAP_SECONDS + 10.0
        with mock.patch("octobot.community.node_journal.recording.sync.time.time", return_value=reconnect_timestamp):
            sync_module.on_user_data_pull_succeeded(sync_user_id="user-1", collection="user-data")

        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.attributes.is_reconnect is True
        assert event_line.attributes.prior_gap_seconds == journal_constants.SYNC_SESSION_GAP_SECONDS + 10.0
        assert event_line.attributes.connection_sequence == 2

    def test_startup_reset_forces_reconnect_even_within_gap(self, journal_persisted_state):
        journal_persisted_state.last_user_data_pull_at = 5_000.0
        journal_persisted_state.connection_sequence = 3
        journal_state.save_persisted_state(journal_persisted_state)
        sync_module.reset_sync_tracker_after_node_startup()

        with mock.patch("octobot.community.node_journal.recording.sync.time.time", return_value=5_100.0):
            sync_module.on_user_data_pull_succeeded(sync_user_id="user-1", collection="user-data")

        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.attributes.is_reconnect is True
        assert event_line.attributes.prior_gap_seconds == 100.0
        assert event_line.attributes.connection_sequence == 4
