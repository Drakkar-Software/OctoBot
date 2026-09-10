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

import octobot_commons.configuration as configuration

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.safe as journal_safe_module
import octobot.community.node_journal.state as journal_state


class TestRunJournalOperation:
    def test_returns_operation_result(self):
        result = journal_safe_module.run_journal_operation("test_op", lambda: 42, default=None)
        assert result == 42

    def test_returns_default_on_exception(self):
        def failing_operation():
            raise RuntimeError("boom")

        result = journal_safe_module.run_journal_operation(
            "test_op",
            failing_operation,
            default="fallback",
        )
        assert result == "fallback"


class TestRecordUnknownEvent:
    def test_returns_stub_with_recorded_false(self, journal_persisted_state):
        event_line = journal_module.record("not_a_real_event")
        assert event_line.recorded is False
        assert event_line.event == journal_events.NodeJournalEvent.UNKNOWN
        assert event_line.attributes.raw_event_name == "not_a_real_event"
        assert journal_module.read_events() == []


class TestRecordMissingErrorCategory:
    def test_returns_stub_with_recorded_false(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={"http_status": 400},
        )
        assert event_line.recorded is False
        assert journal_module.read_events() == []


class TestLoadPersistedStateInvalidConfig:
    def test_treats_non_mapping_journal_section_as_empty(self):
        config_mock = mock.Mock(spec=configuration.Configuration)
        config_mock.config = {journal_constants.CONFIG_JOURNAL_SECTION: "invalid"}
        journal_state.bind_config(config_mock)
        state = journal_state.load_persisted_state()
        assert state.install_id
