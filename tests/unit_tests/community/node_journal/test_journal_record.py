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

import pytest

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.sanitize as journal_sanitize
import octobot.community.node_journal.state as journal_state


class TestRecord:
    def test_writes_event_line_with_core_metadata(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=1_234.5,
        )
        assert event_line["event"] == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value
        assert event_line["timestamp"] == 1_234.5
        assert event_line["session_id"] == journal_state.get_session_id()
        assert event_line["install_id"] == journal_persisted_state.install_id
        assert event_line["app_version"] == octobot_constants.LONG_VERSION
        assert event_line["distribution"] == journal_constants.DISTRIBUTION_NODE
        assert event_line["onboarding_complete"] is False
        assert event_line["attributes"] == {"configured": True}

    def test_accepts_string_event_name(self, journal_persisted_state):
        event_line = journal_module.record(
            "wallet_setup_attempt",
            attributes={"node_type": "node", "setup_method": "api"},
            timestamp=10.0,
        )
        assert event_line["event"] == "wallet_setup_attempt"

    def test_unknown_event_raises(self):
        with pytest.raises(ValueError, match="Unknown journal event"):
            journal_module.record("not_a_real_event")

    def test_skips_none_attribute_values(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node", "setup_method": None},
            timestamp=1.0,
        )
        assert event_line["attributes"] == {"node_type": "node"}

    def test_coerces_non_scalar_attributes_to_string(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": {"nested": True}},
            timestamp=1.0,
        )
        assert event_line["attributes"]["node_type"] == "{'nested': True}"

    def test_failure_event_requires_error_category(self, journal_persisted_state):
        with pytest.raises(ValueError, match="requires error_category"):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
                attributes={"http_status": 400},
            )

    def test_failure_event_defaults_empty_error_message(self, journal_persisted_state):
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={
                "error_category": "ValueError",
                "http_status": 400,
            },
            timestamp=2.0,
        )
        assert event_line["attributes"]["error_message"] == ""

    def test_sanitizes_error_message_attribute(self, journal_persisted_state):
        raw_message = "api_key=supersecret contact user@example.com"
        event_line = journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
            attributes={
                "error_category": "RuntimeError",
                "error_message": raw_message,
            },
            timestamp=3.0,
        )
        assert event_line["attributes"]["error_message"] == journal_sanitize.sanitize_error_message(raw_message)

    def test_first_automation_started_marks_persisted_state(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
            attributes={"automation_id": "auto-1"},
            timestamp=500.0,
        )
        persisted_state = journal_state.load_persisted_state()
        assert persisted_state.first_automation_started_at == 500.0
        assert persisted_state.onboarding_complete is True

    def test_read_events_returns_persisted_lines(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
            attributes={"wallet_configured": False, "new_install": True, "reconciled": False},
            timestamp=1.0,
        )
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0]["event"] == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED.value


class TestSanitizeErrorMessage:
    def test_empty_input_returns_empty_string(self):
        assert journal_sanitize.sanitize_error_message(None) == ""
        assert journal_sanitize.sanitize_error_message("") == ""

    def test_redacts_eth_address(self):
        message = "transfer failed for 0x0000000000000000000000000000000000000001"
        assert journal_sanitize.sanitize_error_message(message) == "transfer failed for [redacted-address]"

    def test_redacts_bech32_address(self):
        message = "wallet bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh invalid"
        sanitized = journal_sanitize.sanitize_error_message(message)
        assert "bc1q" not in sanitized
        assert "[redacted-address]" in sanitized

    def test_redacts_api_key_like_secrets(self):
        message = "auth failed: api_key=abc123xyz"
        assert journal_sanitize.sanitize_error_message(message) == "auth failed: [redacted-secret]"

    def test_redacts_email_and_home_path(self):
        message = "notify user@example.com at /Users/alice/octobot/logs"
        sanitized = journal_sanitize.sanitize_error_message(message)
        assert "user@example.com" not in sanitized
        assert "/Users/alice" not in sanitized
        assert "[redacted-email]" in sanitized
        assert "[redacted-path]" in sanitized

    def test_truncates_long_messages(self):
        long_message = "x" * (journal_constants.ERROR_MESSAGE_MAX_LENGTH + 20)
        sanitized = journal_sanitize.sanitize_error_message(long_message)
        assert len(sanitized) == journal_constants.ERROR_MESSAGE_MAX_LENGTH
        assert sanitized.endswith("…")
