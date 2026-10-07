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

import octobot.constants as octobot_constants
import octobot_commons.configuration as configuration

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state


class TestRecord:
    def test_writes_event_line_with_core_metadata(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=1_234.5,
        )
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED
        assert event_line.timestamp == 1_234.5
        assert event_line.session_id == journal_state.get_session_id()
        assert event_line.install_id == journal_persisted_state.install_id
        assert event_line.app_version == octobot_constants.LONG_VERSION
        assert event_line.distribution == journal_constants.DISTRIBUTION_NODE
        assert event_line.onboarding_complete is False
        assert event_line.attributes.to_dict() == {"configured": True}

    def test_accepts_string_event_name(self, journal_persisted_state):
        event_line = journal_module.record(
            "wallet_setup_attempt",
            attributes={"node_type": "node", "setup_method": "api"},
            timestamp=10.0,
        )
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT

    def test_unknown_event_returns_stub(self):
        event_line = journal_module.record("not_a_real_event")
        assert event_line.recorded is False
        assert event_line.event == journal_events.NodeJournalEvent.UNKNOWN
        assert event_line.attributes.raw_event_name == "not_a_real_event"

    def test_skips_none_attribute_values(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node", "setup_method": None},
            timestamp=1.0,
        )
        assert event_line.attributes.to_dict() == {"node_type": "node"}

    def test_coerces_non_scalar_attributes_to_string(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": {"nested": True}},
            timestamp=1.0,
        )
        assert event_line.attributes.node_type == "{'nested': True}"

    def test_failure_event_requires_error_category(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={"http_status": 400},
        )
        assert event_line.recorded is False

    def test_failure_event_omits_error_message_when_absent(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={
                "error_category": "ValueError",
                "http_status": 400,
            },
            timestamp=2.0,
        )
        assert event_line.attributes.error_message is None

    def test_stores_explicit_error_message_as_is(self, journal_persisted_state):
        raw_message = "api_key=supersecret contact user@example.com"
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={
                "error_category": "RuntimeError",
                "error_message": raw_message,
            },
            timestamp=3.0,
        )
        assert event_line.attributes.error_message == raw_message

    def test_first_automation_started_marks_persisted_state(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
            attributes={"automation_id": "auto-1"},
            timestamp=500.0,
        )
        persisted_state = journal_state.load_persisted_state()
        assert persisted_state.first_automation_started_at == 500.0
        assert persisted_state.onboarding_complete is True

    def test_read_events_roundtrips_persisted_envelope_fields(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
            attributes={"wallet_configured": False, "new_install": True, "reconciled": False},
            timestamp=1.0,
        )
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED
        assert event_line.session_id == journal_state.get_session_id()
        assert event_line.install_id == journal_persisted_state.install_id
        assert event_line.app_version == octobot_constants.LONG_VERSION

    def test_read_events_returns_persisted_lines(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
            attributes={"wallet_configured": False, "new_install": True, "reconciled": False},
            timestamp=1.0,
        )
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0].event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED


class TestRecordFailure:
    def test_does_not_persist_exception_text_when_only_error_given(self, journal_persisted_state):
        event_line = journal_module.record_failure(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            error=ValueError("secret leak"),
            attributes={"http_status": 400},
        )
        assert event_line.attributes.error_category == "ValueError"
        assert event_line.attributes.error_message is None

    def test_stores_explicit_error_message(self, journal_persisted_state):
        event_line = journal_module.record_failure(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            error=ValueError("ignored"),
            error_message="transfer failed",
            attributes={"http_status": 400},
        )
        assert event_line.attributes.error_category == "ValueError"
        assert event_line.attributes.error_message == "transfer failed"


class TestSanitizeEventAttributes:
    def test_preserves_explicit_error_message(self):
        raw_message = "api_key=supersecret contact user@example.com"
        attributes = journal_models.JournalEventAttributes(
            error_category="RuntimeError",
            error_message=raw_message,
        )
        sanitized = journal_module.sanitize_event_attributes(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes,
        )
        assert sanitized.error_message == raw_message

    def test_failure_event_omits_error_message_when_absent(self):
        attributes = journal_models.JournalEventAttributes(
            error_category="ValueError",
            http_status=400,
        )
        sanitized = journal_module.sanitize_event_attributes(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes,
        )
        assert sanitized.error_message is None

    def test_non_failure_event_skips_error_message_default(self):
        attributes = journal_models.JournalEventAttributes(http_status=400)
        sanitized = journal_module.sanitize_event_attributes(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes,
        )
        assert sanitized.error_message is None


class TestRunJournalOperation:
    def test_returns_operation_result(self):
        result = journal_module.run_journal_operation("test_op", lambda: 42, default=None)
        assert result == 42

    def test_returns_default_on_exception(self):
        def failing_operation():
            raise RuntimeError("boom")

        result = journal_module.run_journal_operation(
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
