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


class TestRecordStrategyCreateSucceeded:
    def test_records_strategy_metadata(self, journal_persisted_state):
        journal_recording.record_strategy_create_succeeded(
            strategy_id="strategy-create-1",
            configuration_type="generic_process",
            user_action_id="ua-create-strategy",
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED.value
        assert events[0]["attributes"]["strategy_id"] == "strategy-create-1"
        assert events[0]["attributes"]["configuration_type"] == "generic_process"
        assert events[0]["attributes"]["user_action_id"] == "ua-create-strategy"


class TestRecordStrategyEditSucceeded:
    def test_records_strategy_metadata(self, journal_persisted_state):
        journal_recording.record_strategy_edit_succeeded(
            strategy_id="strategy-edit-1",
            configuration_type="market_making",
            user_action_id="ua-edit-strategy",
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED.value
        assert events[0]["attributes"]["strategy_id"] == "strategy-edit-1"
        assert events[0]["attributes"]["configuration_type"] == "market_making"
        assert events[0]["attributes"]["user_action_id"] == "ua-edit-strategy"
