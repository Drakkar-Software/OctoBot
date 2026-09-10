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
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


class TestJournalCapEviction:
    def test_evicts_post_onboarding_events_before_pre_onboarding_events(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=10)

        journal_persisted_state.first_automation_started_at = 100.0
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        for event_index in range(5):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"protected-{event_index}"},
                timestamp=10.0 + event_index,
            )
        for event_index in range(10):
            journal_module.record(
                journal_events.NodeJournalEvent.AUTOMATION_STARTED,
                attributes={
                    "automation_id": f"auto-{event_index}",
                    "automation_count": event_index + 1,
                    "octobot_kind": "default",
                    "flow_subtype": None,
                },
                timestamp=200.0 + event_index,
            )

        events = journal_module.read_events()
        assert len(events) == 10
        protected_timestamps = {event_line.timestamp for event_line in events if event_line.timestamp < 100.0}
        evictable_timestamps = {event_line.timestamp for event_line in events if event_line.timestamp >= 100.0}
        assert protected_timestamps == {10.0, 11.0, 12.0, 13.0, 14.0}
        assert evictable_timestamps == {205.0, 206.0, 207.0, 208.0, 209.0}

    def test_does_not_trim_when_under_cap(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=10)

        for event_index in range(3):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"method-{event_index}"},
                timestamp=float(event_index),
            )

        assert len(journal_module.read_events()) == 3
