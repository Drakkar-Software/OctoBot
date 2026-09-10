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


class TestRecordSchedulerInitFailed:
    def test_records_init_phase_and_backend(self, journal_persisted_state):
        journal_recording.record_scheduler_init_failed(
            init_phase="dbos_create",
            backend="sqlite",
            error=RuntimeError("dbos unavailable"),
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.SCHEDULER_INIT_FAILED.value
        assert events[0]["attributes"]["init_phase"] == "dbos_create"
        assert events[0]["attributes"]["backend"] == "sqlite"
        assert events[0]["attributes"]["error_category"] == "RuntimeError"
