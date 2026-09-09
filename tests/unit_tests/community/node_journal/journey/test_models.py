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

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.storage_hydration as journal_storage_hydration
import octobot.community.node_journal.state as journal_state

_EVENT = journal_enums.JournalEventLineField
_CTX = journal_enums.JournalStorageContextField
_MANIFEST = journal_enums.JournalManifestField


class TestJournalEventAttributesToDict:
    def test_roundtrips_scalar_fields(self):
        attributes = journal_models.JournalEventAttributes(
            account_id="acc-1",
            configured=True,
            http_status=400,
        )
        restored = journal_models.JournalEventAttributes.from_dict(attributes.to_dict())
        assert restored == attributes


class TestJournalEventAttributesFromDict:
    def test_ignores_unknown_keys(self):
        attributes = journal_models.JournalEventAttributes.from_dict(
            {"account_id": "acc-1", "unknown_field": "ignored"},
        )
        assert attributes.account_id == "acc-1"


class TestJournalEventAttributesMergeIgnoresUnknownOverrideKeys:
    def test_ignores_unknown_override_keys(self):
        base_attributes = journal_models.JournalEventAttributes(account_id="acc-1")
        merged = journal_models.JournalEventAttributes.merge(
            base_attributes,
            {"http_status": 400, "unknown": "ignored"},
        )
        assert merged.account_id == "acc-1"
        assert merged.http_status == 400


class TestJournalEventAttributesMergeOverridesKnownFields:
    def test_overrides_known_fields(self):
        base_attributes = journal_models.JournalEventAttributes(account_id="acc-1")
        merged = journal_models.JournalEventAttributes.merge(
            base_attributes,
            {"http_status": 400},
        )
        assert merged.account_id == "acc-1"
        assert merged.http_status == 400


class TestJournalEventLineToStorageDict:
    def test_omits_envelope_fields(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        serialized = event_line.to_storage_dict()
        assert _EVENT.INSTALL_ID.value not in serialized
        assert _EVENT.SESSION_ID.value not in serialized
        assert serialized[_EVENT.EVENT.value] == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value


class TestJournalEventLineToDictEventSerializesAsString:
    def test_event_serializes_as_string(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        serialized = event_line.to_dict()
        assert serialized[_EVENT.EVENT.value] == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value
        assert isinstance(serialized[_EVENT.EVENT.value], str)


class TestJournalEventLineToDictOmitsRecordedWhenTrue:
    def test_omits_recorded_when_true(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        assert _EVENT.RECORDED.value not in event_line.to_dict()


class TestJournalEventLineToDictIncludesRecordedWhenFalse:
    def test_includes_recorded_when_false(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
            recorded=False,
        )
        assert event_line.to_dict()[_EVENT.RECORDED.value] is False


class TestJournalEventLineToDictRoundtripsEventLine:
    def test_roundtrips_event_line(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1_234.5,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        restored = journal_models.JournalEventLine.from_dict(event_line.to_dict())
        assert restored.event == event_line.event
        assert restored.timestamp == event_line.timestamp
        assert restored.session_id == event_line.session_id
        assert restored.install_id == event_line.install_id
        assert restored.attributes == event_line.attributes
        assert restored.recorded is True


class TestJournalEventLineFromDict:
    def test_preserves_recorded_false(self):
        event_line = journal_models.JournalEventLine.from_dict(
            {
                _EVENT.EVENT.value: journal_events.NodeJournalEvent.WALLET_SETUP_FAILED.value,
                _EVENT.TIMESTAMP.value: 1.0,
                _EVENT.SESSION_ID.value: "",
                _EVENT.INSTALL_ID.value: "",
                _EVENT.APP_VERSION.value: "1.0.0",
                _EVENT.DISTRIBUTION.value: "node",
                _EVENT.ONBOARDING_COMPLETE.value: False,
                _EVENT.ATTRIBUTES.value: {"error_category": "ValueError"},
                _EVENT.RECORDED.value: False,
            }
        )
        assert event_line.recorded is False


class TestJournalEventLineFromDictLegacyEvent:
    def test_maps_unknown_event_string_to_unknown_with_raw_event_name(self):
        event_line = journal_models.JournalEventLine.from_dict(
            {
                _EVENT.EVENT.value: "legacy_custom_event",
                _EVENT.TIMESTAMP.value: 1.0,
                _EVENT.SESSION_ID.value: "session-1",
                _EVENT.INSTALL_ID.value: "install-1",
                _EVENT.APP_VERSION.value: "1.0.0",
                _EVENT.DISTRIBUTION.value: "node",
                _EVENT.ONBOARDING_COMPLETE.value: False,
                _EVENT.ATTRIBUTES.value: {},
            }
        )
        assert event_line.event == journal_events.NodeJournalEvent.UNKNOWN
        assert event_line.attributes.raw_event_name == "legacy_custom_event"


class TestJournalEventLineFromDictMissingAttributes:
    def test_uses_empty_attributes_when_missing(self):
        event_line = journal_models.JournalEventLine.from_dict(
            {
                _EVENT.EVENT.value: journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET.value,
                _EVENT.TIMESTAMP.value: 1.0,
                _EVENT.SESSION_ID.value: "session-1",
                _EVENT.INSTALL_ID.value: "install-1",
                _EVENT.APP_VERSION.value: "1.0.0",
                _EVENT.DISTRIBUTION.value: "node",
                _EVENT.ONBOARDING_COMPLETE.value: False,
            }
        )
        assert event_line.attributes == journal_models.JournalEventAttributes()


class TestJournalEventLineHydrateStorageEventMissingAttributes:
    def test_hydrates_event_without_attributes(self):
        persisted_state = journal_state.JournalPersistedState(install_id="install-1")
        event_line = journal_storage_hydration.hydrate_storage_event(
            {
                _EVENT.EVENT.value: journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET.value,
                _EVENT.TIMESTAMP.value: 1.0,
            },
            {_CTX.SESSION_ID.value: "session-1", _CTX.APP_VERSION.value: "1.0.0"},
            {
                _MANIFEST.INSTALL_ID.value: "install-1",
                _MANIFEST.SCHEMA.value: journal_constants.JOURNAL_SCHEMA_VERSION,
            },
            persisted_state,
        )
        assert event_line.attributes == journal_models.JournalEventAttributes()
        serialized = event_line.to_storage_dict()
        assert _EVENT.ATTRIBUTES.value not in serialized
        assert serialized[_EVENT.EVENT.value] == journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET.value


class TestUploadEnvelopeToDictMissingEventAttributes:
    def test_serializes_envelope_with_attribute_less_event(self):
        event_line = journal_models.JournalEventLine.from_dict(
            {
                _EVENT.EVENT.value: journal_events.NodeJournalEvent.UI_CLIENT_STORAGE_RESET.value,
                _EVENT.TIMESTAMP.value: 1.0,
                _EVENT.SESSION_ID.value: "session-1",
                _EVENT.INSTALL_ID.value: "install-1",
                _EVENT.APP_VERSION.value: "1.0.0",
                _EVENT.DISTRIBUTION.value: "node",
                _EVENT.ONBOARDING_COMPLETE.value: False,
            }
        )
        journey_summary = journal_models.JourneySummary(
            onboarding_complete=False,
            furthest_step_reached=None,
            last_successful_step=None,
            first_failure=None,
            retry_counts={},
            step_durations_seconds={},
            step_deltas_seconds={},
            external_connect_count=0,
            first_external_connect_at=None,
            last_external_connect_at=None,
            longest_connect_gap_seconds=None,
            ui_blocking_issues_count=0,
        )
        upload_envelope = journal_models.UploadEnvelope(
            install_id="install-1",
            app_version="1.0.0",
            onboarding_started_at=1_000.0,
            onboarding_complete=False,
            journey_summary=journey_summary,
            events=[event_line],
            uploaded=False,
            ready=True,
            event_count=1,
        )
        serialized = upload_envelope.to_dict()
        assert serialized["events"] == [event_line.to_storage_dict()]


class TestFirstFailureInfoToDict:
    def test_roundtrips_failure_info(self):
        failure_info = journal_models.FirstFailureInfo(
            event=journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED.value,
            timestamp=100.0,
            error_category="ValueError",
            error_message="invalid",
        )
        restored = journal_models.FirstFailureInfo.from_dict(failure_info.to_dict())
        assert restored == failure_info


class TestFirstFailureInfoFromDict:
    def test_returns_none_for_empty_payload(self):
        assert journal_models.FirstFailureInfo.from_dict(None) is None


class TestJourneySummaryToDict:
    def test_roundtrips_summary(self):
        journey_summary = journal_models.JourneySummary(
            onboarding_complete=True,
            furthest_step_reached="wallet_setup_succeeded",
            last_successful_step="wallet_setup_succeeded",
            first_failure=None,
            retry_counts={"account_validation_failed": 1},
            step_durations_seconds={"wallet_setup": 10.0},
            step_deltas_seconds={"wallet_setup_to_external_connect": 5.0},
            external_connect_count=2,
            first_external_connect_at=1_020.0,
            last_external_connect_at=1_030.0,
            longest_connect_gap_seconds=5.0,
            ui_blocking_issues_count=2,
        )
        restored_dict = journey_summary.to_dict()
        assert restored_dict["onboarding_complete"] is True
        assert restored_dict["retry_counts"] == {"account_validation_failed": 1}
        assert restored_dict["ui_blocking_issues_count"] == 2


class TestUploadEnvelopeToDict:
    def test_roundtrips_envelope(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        journey_summary = journal_models.JourneySummary(
            onboarding_complete=False,
            furthest_step_reached=None,
            last_successful_step=None,
            first_failure=None,
            retry_counts={},
            step_durations_seconds={},
            step_deltas_seconds={},
            external_connect_count=0,
            first_external_connect_at=None,
            last_external_connect_at=None,
            longest_connect_gap_seconds=None,
            ui_blocking_issues_count=0,
        )
        upload_envelope = journal_models.UploadEnvelope(
            install_id="install-1",
            app_version="1.0.0",
            onboarding_started_at=1_000.0,
            onboarding_complete=False,
            journey_summary=journey_summary,
            events=[event_line],
            uploaded=False,
            ready=True,
            event_count=1,
            note="beta",
        )
        serialized = upload_envelope.to_dict()
        assert serialized["events"] == [event_line.to_storage_dict()]
        assert _EVENT.INSTALL_ID.value not in serialized["events"][0]
        restored = journal_models.UploadEnvelope(
            **{
                key: value
                for key, value in upload_envelope.to_dict().items()
                if key != "journey_summary" and key != "events"
            },
            journey_summary=journey_summary,
            events=[journal_models.JournalEventLine.from_dict(event_line.to_dict())],
        )
        assert restored.install_id == upload_envelope.install_id
        assert restored.note == upload_envelope.note
        assert len(restored.events) == 1
