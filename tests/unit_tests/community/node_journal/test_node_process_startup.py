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

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording
import octobot.community.node_journal.startup as journal_startup


class TestRecordProcessStartupFailed:
    def test_records_startup_failure_metadata(self, journal_persisted_state):
        journal_recording.record_process_startup_failed(
            startup_phase="node_api_start",
            error=RuntimeError("api failed"),
            force_exit=False,
            wallet_configured=True,
            new_install=False,
            reconciled=True,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED
        assert event_line.attributes.startup_phase == "node_api_start"
        assert event_line.attributes.force_exit is False
        assert event_line.attributes.wallet_configured is True
        assert event_line.attributes.error_category == "RuntimeError"


class TestRecordNodeStartupFailed:
    def test_initializes_journal_and_records_failure(self, journal_persisted_state):
        config_mock = mock.Mock()
        snapshot = journal_startup.ExistingConfigSnapshot(
            wallet_configured=False,
            account_count=0,
            automation_count=0,
            reconciled=False,
        )
        with (
            mock.patch.object(journal_startup, "build_existing_config_snapshot", return_value=snapshot),
            mock.patch("octobot.community.node_journal.startup.journal_module.initialize_for_config") as init_mock,
        ):
            journal_startup.record_node_startup_failed(
                RuntimeError("startup boom"),
                startup_phase="prepare",
                force_exit=True,
                config=config_mock,
            )
        init_mock.assert_called_once_with(config_mock)
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED
        assert event_line.attributes.startup_phase == "prepare"
        assert event_line.attributes.new_install is True
