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

import io
import json
import zipfile

import mock

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module

_EVENT = journal_enums.JournalEventLineField

from tentacles.Services.Interfaces.node_api_interface.api.routes import feedback as feedback_routes


def _decode_export_zip_response(response) -> dict:
    archive = io.BytesIO(response.body)
    with zipfile.ZipFile(archive) as zip_file:
        names = zip_file.namelist()
        assert names == [feedback_routes.FEEDBACK_JOURNAL_JSON_FILENAME]
        json_text = zip_file.read(feedback_routes.FEEDBACK_JOURNAL_JSON_FILENAME).decode()
    return json.loads(json_text)


class TestBuildFeedbackJournalZip:
    def test_builds_single_json_member_with_zip_magic(self, journal_persisted_state):
        envelope = feedback_routes._build_feedback_upload_envelope(note="zip test")
        archive = feedback_routes.build_feedback_journal_zip(envelope)
        assert archive[0:2] == b"PK"
        payload = _decode_export_zip_response(
            type("Response", (), {"body": archive})(),
        )
        assert payload["note"] == "zip test"


class TestBuildFeedbackPreview:
    def test_builds_journey_summary_and_upload_envelope(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=10.0,
        )

        preview = feedback_routes._build_feedback_preview()

        assert preview.journey_summary["last_successful_step"] == (
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value
        )
        assert preview.upload_envelope.install_id == journal_persisted_state.install_id
        assert preview.upload_envelope.app_version == octobot_constants.LONG_VERSION
        assert preview.upload_envelope.event_count == 1
        assert preview.upload_envelope.ready is True
        assert preview.upload_envelope.uploaded is False


class TestBuildFeedbackPreviewAttributeLessEvent:
    def test_serializes_ui_client_storage_reset_without_attributes(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET,
            timestamp=10.0,
        )

        preview = feedback_routes._build_feedback_preview()

        assert preview.upload_envelope.event_count == 1
        assert preview.upload_envelope.events[0][_EVENT.EVENT.value] == (
            journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET.value
        )
        assert _EVENT.ATTRIBUTES.value not in preview.upload_envelope.events[0]


class TestBuildFeedbackUploadEnvelope:
    def test_includes_optional_note(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
            attributes={"wallet_configured": False, "new_install": True, "reconciled": False},
            timestamp=1.0,
        )

        envelope = feedback_routes._build_feedback_upload_envelope(note="manual export")

        assert envelope.note == "manual export"
        assert envelope.event_count == 1

    def test_upload_events_use_storage_shape(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=1.0,
        )
        envelope = feedback_routes._build_feedback_upload_envelope()
        assert len(envelope.events) == 1
        assert _EVENT.INSTALL_ID.value not in envelope.events[0]
        assert _EVENT.SESSION_ID.value not in envelope.events[0]
        assert envelope.events[0][_EVENT.EVENT.value] == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value


class TestBuildFeedbackPreviewWhenJournalDisabled:
    def test_returns_empty_events_when_journal_disabled(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=10.0,
        )
        with mock.patch.dict(
            "os.environ",
            {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"},
        ):
            preview = feedback_routes._build_feedback_preview()
        assert preview.upload_envelope.event_count == 0
        assert preview.upload_envelope.events == []
        assert preview.journey_summary["last_successful_step"] is None


class TestExportFeedback:
    def test_combines_note_and_issue_url(self, journal_persisted_state):
        request_body = feedback_routes.FeedbackUploadRequest(
            note="sync issue",
            issue_url="https://github.com/example/issues/1",
        )

        response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)

        assert "sync issue" in payload["note"]
        assert "issue_url: https://github.com/example/issues/1" in payload["note"]

    def test_includes_ui_error_name_on_envelope(self, journal_persisted_state):
        request_body = feedback_routes.FeedbackUploadRequest(ui_error_name="boot_failed")

        response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)

        assert payload["ui_error_name"] == "boot_failed"
        assert payload["ui_error_route"] is None

    def test_includes_ui_error_route_for_route_errors(self, journal_persisted_state):
        request_body = feedback_routes.FeedbackUploadRequest(
            ui_error_name="route_error",
            ui_error_route="/app/x",
        )

        response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)

        assert payload["ui_error_name"] == "route_error"
        assert payload["ui_error_route"] == "/app/x"

    def test_note_and_ui_error_name_without_context_in_note(self, journal_persisted_state):
        request_body = feedback_routes.FeedbackUploadRequest(
            note="user detail",
            ui_error_name="auth_broken",
        )

        response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)

        assert payload["note"] == "user detail"
        assert payload["ui_error_name"] == "auth_broken"
        assert "failure_kind" not in (payload["note"] or "")


class TestFeedbackRoutes:
    def test_export_route_registered_without_upload(self):
        paths = {route.path for route in feedback_routes.router.routes}
        assert "/export" in paths
        assert "/upload" not in paths
        assert "/preview" in paths


class TestExportFeedbackWhenJournalDisabled:
    def test_returns_note_only_without_journal_events(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=10.0,
        )
        request_body = feedback_routes.FeedbackUploadRequest(note="note only")
        with mock.patch.dict(
            "os.environ",
            {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"},
        ):
            response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)
        assert payload["event_count"] == 0
        assert payload["events"] == []
        assert "note only" in (payload["note"] or "")

    def test_includes_ui_error_name_when_journal_disabled(
        self,
        journal_persisted_state,
    ):
        request_body = feedback_routes.FeedbackUploadRequest(
            note="note only",
            ui_error_name="insecure_context",
        )
        with mock.patch.dict(
            "os.environ",
            {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"},
        ):
            response = feedback_routes.export_feedback(body=request_body)
        payload = _decode_export_zip_response(response)
        assert payload["ui_error_name"] == "insecure_context"
