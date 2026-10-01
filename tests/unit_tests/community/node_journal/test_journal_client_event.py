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
import pytest
from fastapi import HTTPException

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module

from tentacles.Services.Interfaces.node_api_interface.api.routes import journal_client_event as journal_client_event_routes


class TestValidateClientEvent:
    def test_allows_ui_journal_events(self):
        parsed_event = journal_client_event_routes._validate_client_event(
            journal_events.NodeJournalEvent.UI_BOOT_FAILED.value,
        )
        assert parsed_event == journal_events.NodeJournalEvent.UI_BOOT_FAILED

    def test_rejects_unknown_event(self):
        with pytest.raises(HTTPException) as raised_error:
            journal_client_event_routes._validate_client_event("not_a_real_event")
        assert raised_error.value.status_code == 400
        assert "Unknown journal event" in raised_error.value.detail

    def test_rejects_non_ui_event(self):
        with pytest.raises(HTTPException) as raised_error:
            journal_client_event_routes._validate_client_event(
                journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
            )
        assert raised_error.value.status_code == 400
        assert "Event not allowed" in raised_error.value.detail


class TestBuildClientEventAttributes:
    def test_includes_client_instance_id(self):
        request_body = journal_client_event_routes.JournalClientEventRequest(
            event=journal_events.NodeJournalEvent.UI_BOOT_FAILED.value,
            client_instance_id="client-123",
            attributes={"screen": "dashboard"},
        )
        attributes = journal_client_event_routes._build_client_event_attributes(request_body)
        assert attributes["client_instance_id"] == "client-123"
        assert attributes["screen"] == "dashboard"

    def test_rejects_oversized_attributes_payload(self):
        request_body = journal_client_event_routes.JournalClientEventRequest(
            event=journal_events.NodeJournalEvent.UI_BOOT_FAILED.value,
            attributes={"blob": "x" * 5_000},
        )
        with pytest.raises(HTTPException) as raised_error:
            journal_client_event_routes._build_client_event_attributes(request_body)
        assert raised_error.value.status_code == 400
        assert "too large" in raised_error.value.detail


class TestRecordJournalClientEvent:
    def test_returns_recorded_false_when_journal_disabled(self, journal_persisted_state):
        request_body = journal_client_event_routes.JournalClientEventRequest(
            event=journal_events.NodeJournalEvent.UI_BOOT_FAILED.value,
            client_instance_id="client-disabled",
        )
        with mock.patch.dict(
            "os.environ",
            {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"},
        ):
            response = journal_client_event_routes.record_journal_client_event(request_body)
        assert response.recorded is False
        assert response.event == journal_events.NodeJournalEvent.UI_BOOT_FAILED.value
        assert journal_module.read_events() == []

    def test_records_allowlisted_event(self, journal_persisted_state):
        request_body = journal_client_event_routes.JournalClientEventRequest(
            event=journal_events.NodeJournalEvent.UI_FATAL_RENDER_ERROR.value,
            client_instance_id="client-abc",
            attributes={"route": "/settings"},
        )

        response = journal_client_event_routes.record_journal_client_event(request_body)

        assert response.event == journal_events.NodeJournalEvent.UI_FATAL_RENDER_ERROR.value
        assert response.install_id == journal_persisted_state.install_id
        assert response.attributes["client_instance_id"] == "client-abc"
        assert response.attributes["route"] == "/settings"
