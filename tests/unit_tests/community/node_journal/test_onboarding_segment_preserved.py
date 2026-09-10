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

import json
import os

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


class TestOnboardingSegmentPreserved:
    def test_onboarding_events_written_to_segment_file(self, journal_persisted_state, journal_user_root):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node", "setup_method": "api"},
            timestamp=1.0,
        )
        segment_path = os.path.join(
            str(journal_user_root),
            journal_constants.JOURNAL_DIR_NAME,
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        assert os.path.isfile(segment_path)
        with open(segment_path, encoding="utf-8") as segment_file:
            assert "wallet_setup_attempt" in segment_file.read()

    def test_post_onboarding_events_skip_segment_file(self, journal_persisted_state, journal_user_root):
        journal_persisted_state.first_automation_started_at = 50.0
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        journal_module.record(
            journal_events.NodeJournalEvent.AUTOMATION_STARTED,
            attributes={
                "automation_id": "auto-1",
                "automation_count": 1,
                "octobot_kind": "default",
                "flow_subtype": None,
            },
            timestamp=60.0,
        )

        segment_path = os.path.join(
            str(journal_user_root),
            journal_constants.JOURNAL_DIR_NAME,
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        assert not os.path.isfile(segment_path)

    def test_segment_events_survive_main_file_cap_eviction(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=3)

        for event_index in range(5):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"method-{event_index}"},
                timestamp=float(event_index),
            )

        events = journal_module.read_events()
        setup_methods = [
            event_line.attributes.setup_method
            for event_line in events
            if event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT
        ]
        assert setup_methods == ["method-0", "method-1", "method-2", "method-3", "method-4"]


class TestLegacyJsonlEventRead:
    def test_reads_obsolete_event_name_as_unknown(self, journal_persisted_state, journal_user_root):
        events_path = os.path.join(
            str(journal_user_root),
            journal_constants.JOURNAL_DIR_NAME,
            journal_constants.EVENTS_FILE_NAME,
        )
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        legacy_event_line = {
            "event": "legacy_custom_event",
            "timestamp": 12.0,
            "session_id": "session-1",
            "install_id": journal_persisted_state.install_id,
            "app_version": "1.0.0",
            "distribution": journal_constants.DISTRIBUTION_NODE,
            "onboarding_complete": False,
            "attributes": {},
        }
        with open(events_path, "w", encoding="utf-8") as events_file:
            events_file.write(json.dumps(legacy_event_line) + "\n")
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.UNKNOWN
        assert event_line.attributes.raw_event_name == "legacy_custom_event"
