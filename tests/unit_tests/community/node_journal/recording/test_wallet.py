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


class TestRecordWalletSetupAttempt:
    def test_records_attempt_attributes(self, journal_persisted_state):
        journal_recording.record_wallet_setup_attempt(node_type="node", setup_method="api")
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT
        assert event_line.attributes.to_dict() == {"node_type": "node", "setup_method": "api"}


class TestRecordWalletSetupSucceeded:
    def test_records_configured_flag(self, journal_persisted_state):
        journal_recording.record_wallet_setup_succeeded()
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED
        assert event_line.attributes.to_dict() == {"configured": True}


class TestRecordWalletSetupFailed:
    def test_records_failure_metadata(self, journal_persisted_state):
        journal_recording.record_wallet_setup_failed(
            http_status=400,
            failure_reason="invalid_passphrase",
            error=ValueError("bad passphrase"),
            setup_method="api",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_FAILED
        assert event_line.attributes.http_status == 400
        assert event_line.attributes.failure_reason == "invalid_passphrase"
        assert event_line.attributes.error_category == "ValueError"
        assert event_line.attributes.setup_method == "api"
        assert event_line.attributes.error_message is None

    def test_records_422_wallet_error(self, journal_persisted_state):
        journal_recording.record_wallet_setup_failed(
            http_status=422,
            failure_reason="wallet_error",
            error=ValueError("Passphrase must be at least 8 characters"),
            setup_method="create",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.attributes.http_status == 422
        assert event_line.attributes.failure_reason == "wallet_error"
        assert event_line.attributes.error_message is None

    def test_records_409_already_configured(self, journal_persisted_state):
        journal_recording.record_wallet_setup_failed(
            http_status=409,
            failure_reason="already_configured",
            error=RuntimeError("Node is already configured"),
            setup_method="create",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.attributes.http_status == 409
        assert event_line.attributes.failure_reason == "already_configured"
        assert event_line.attributes.error_message is None

    def test_records_503_service_unavailable(self, journal_persisted_state):
        journal_recording.record_wallet_setup_failed(
            http_status=503,
            failure_reason="service_unavailable",
            error=RuntimeError("Service not initialized"),
            setup_method="import",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.attributes.http_status == 503
        assert event_line.attributes.failure_reason == "service_unavailable"
        assert event_line.attributes.setup_method == "import"
        assert event_line.attributes.error_message is None


class TestRecordWalletOperationFailed:
    def test_records_operation_and_optional_http_status(self, journal_persisted_state):
        journal_recording.record_wallet_operation_failed(
            operation="delete_wallet",
            error=RuntimeError("locked"),
            http_status=409,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_OPERATION_FAILED
        assert event_line.attributes.operation == "delete_wallet"
        assert event_line.attributes.http_status == 409
        assert event_line.attributes.error_category == "RuntimeError"
        assert event_line.attributes.error_message is None
