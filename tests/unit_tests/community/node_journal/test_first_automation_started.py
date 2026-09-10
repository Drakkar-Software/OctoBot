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
import octobot.community.node_journal.state as journal_state

from .test_external_action_events import _minimal_strategy


class TestRecordFirstAutomationStarted:
    def test_records_milestone_attributes(self, journal_persisted_state):
        journal_recording.record_first_automation_started(
            automation_id="auto-1",
            octobot_kind="flow",
            flow_subtype="copy",
            user_action_id="ua-first",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED
        assert event_line.attributes.automation_id == "auto-1"
        assert event_line.attributes.octobot_kind == "flow"
        assert event_line.attributes.user_action_id == "ua-first"


class TestRecordNewAutomationCreated:
    def test_first_automation_emits_only_first_started_milestone(self, journal_persisted_state):
        journal_recording.record_new_automation_created(
            automation_id="auto-first",
            automation_count=1,
            octobot_kind="manual",
            flow_subtype=None,
            is_first_automation=True,
        )
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0].event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED

    def test_second_automation_emits_automation_started(self, journal_persisted_state):
        journal_recording.record_new_automation_created(
            automation_id="auto-second",
            automation_count=2,
            octobot_kind="flow",
            flow_subtype="signal_bot",
            is_first_automation=False,
            source="sync",
        )
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.AUTOMATION_STARTED
        assert event_line.attributes.automation_count == 2
        assert event_line.attributes.source == "sync"


class TestRecordNewAutomationCreatedFromStrategy:
    def test_tracks_first_automation_from_strategy(self, journal_persisted_state):
        strategy_model = _minimal_strategy(strategy_id="strategy-1")
        journal_recording.record_new_automation_created_from_strategy(
            automation_id="auto-from-strategy",
            strategy=strategy_model,
            user_action_id="ua-create-auto",
        )
        events = journal_module.read_events()
        assert events[0].event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED
        persisted_state = journal_state.load_persisted_state()
        assert persisted_state.tracked_automation_ids == ["auto-from-strategy"]

    def test_skips_duplicate_automation_id(self, journal_persisted_state):
        journal_persisted_state.tracked_automation_ids = ["auto-existing"]
        journal_state.save_persisted_state(journal_persisted_state)
        strategy_model = _minimal_strategy(strategy_id="strategy-2")
        journal_recording.record_new_automation_created_from_strategy(
            automation_id="auto-existing",
            strategy=strategy_model,
        )
        assert journal_module.read_events() == []

    def test_does_not_repeat_first_started_when_milestone_already_set(self, journal_persisted_state):
        journal_persisted_state.first_automation_started_at = 100.0
        journal_persisted_state.tracked_automation_ids = []
        journal_state.save_persisted_state(journal_persisted_state)
        strategy_model = _minimal_strategy(strategy_id="strategy-restart")
        journal_recording.record_new_automation_created_from_strategy(
            automation_id="auto-after-reset",
            strategy=strategy_model,
        )
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0].event == journal_events.NodeJournalEvent.AUTOMATION_STARTED
