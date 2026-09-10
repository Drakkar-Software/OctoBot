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


class TestNodeJournalEvent:
    def test_event_values_are_unique_snake_case_strings(self):
        event_values = [event.value for event in journal_events.NodeJournalEvent]
        assert len(event_values) == len(set(event_values))
        for event_value in event_values:
            assert event_value.islower()
            assert " " not in event_value

    def test_failure_events_match_failed_or_errored_suffix(self):
        expected_failure_events = {
            event
            for event in journal_events.NodeJournalEvent
            if event.value.endswith("_failed") or event.value.endswith("_errored")
        }
        assert journal_events.FAILURE_EVENTS == expected_failure_events

    def test_ui_journal_events_are_ui_prefixed(self):
        for event in journal_events.UI_JOURNAL_EVENTS:
            assert event.value.startswith("ui_")

    def test_funnel_step_rank_matches_order(self):
        assert len(journal_events.FUNNEL_STEP_RANK) == len(journal_events.FUNNEL_STEP_ORDER)
        for rank, event in enumerate(journal_events.FUNNEL_STEP_ORDER):
            assert journal_events.FUNNEL_STEP_RANK[event] == rank

    def test_funnel_includes_startup_wallet_external_and_automation_milestones(self):
        funnel_values = {event.value for event in journal_events.FUNNEL_STEP_ORDER}
        assert "node_process_startup_succeeded" in funnel_values
        assert "wallet_setup_succeeded" in funnel_values
        assert "external_interface_connected" in funnel_values
        assert "first_automation_started" in funnel_values
