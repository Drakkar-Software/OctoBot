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
import octobot.community.node_journal.recording as journal_recording


class TestRecordAutomationRunErrored:
    def test_records_error_metadata(self, journal_persisted_state):
        journal_recording.record_automation_run_errored(
            automation_id="auto-error-1",
            error_status="action_execution_error",
            error_origin="workflow",
            error=RuntimeError("automation crashed"),
            retriable=True,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.AUTOMATION_RUN_ERRORED
        assert event_line.attributes.automation_id == "auto-error-1"
        assert event_line.attributes.error_status == "action_execution_error"
        assert event_line.attributes.error_origin == "workflow"
        assert event_line.attributes.retriable is True
        assert event_line.attributes.error_category == "RuntimeError"
