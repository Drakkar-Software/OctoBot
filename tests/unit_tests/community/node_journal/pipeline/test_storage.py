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

import json
import os

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.storage_hydration as journal_storage_hydration
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store

_EVENT = journal_enums.JournalEventLineField
_CTX = journal_enums.JournalStorageContextField
_MANIFEST = journal_enums.JournalManifestField


def _golden_persisted_state() -> journal_state.JournalPersistedState:
    return journal_state.JournalPersistedState(
        install_id="test-install-id",
        onboarding_started_at=1_000.0,
        first_automation_started_at=1060.0,
        onboarding_complete=True,
    )


class TestToStorageDict:
    def test_omits_envelope_fields(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution=journal_constants.DISTRIBUTION_NODE,
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(configured=True),
        )
        serialized = event_line.to_storage_dict()
        assert serialized == {
            _EVENT.EVENT.value: journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
            _EVENT.TIMESTAMP.value: 1.0,
            _EVENT.ATTRIBUTES.value: {"configured": True},
        }

    def test_includes_recorded_false(self):
        event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            timestamp=1.0,
            session_id="session-1",
            install_id="install-1",
            app_version="1.0.0",
            distribution=journal_constants.DISTRIBUTION_NODE,
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(),
            recorded=False,
        )
        assert event_line.to_storage_dict()[_EVENT.RECORDED.value] is False


class TestHydrateStorageEvent:
    def test_roundtrips_storage_event(self):
        manifest = {
            _MANIFEST.SCHEMA.value: journal_constants.JOURNAL_SCHEMA_VERSION,
            _MANIFEST.INSTALL_ID.value: "install-1",
        }
        ctx = {
            _CTX.SESSION_ID.value: "session-1",
            _CTX.APP_VERSION.value: "1.0.0",
        }
        persisted_state = journal_state.JournalPersistedState(install_id="install-1")
        event_line = journal_storage_hydration.hydrate_storage_event(
            {
                _EVENT.EVENT.value: journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
                _EVENT.TIMESTAMP.value: 10.0,
                _EVENT.ATTRIBUTES.value: {"configured": True},
            },
            ctx,
            manifest,
            persisted_state,
        )
        assert event_line.install_id == "install-1"
        assert event_line.session_id == "session-1"
        assert event_line.app_version == "1.0.0"
        assert event_line.distribution == journal_constants.DISTRIBUTION_NODE
        assert event_line.onboarding_complete is False

    def test_onboarding_complete_before_cutoff(self):
        persisted_state = _golden_persisted_state()
        event_line = journal_storage_hydration.hydrate_storage_event(
            {_EVENT.EVENT.value: "wallet_setup_succeeded", _EVENT.TIMESTAMP.value: 1050.0},
            {_CTX.SESSION_ID.value: "s", _CTX.APP_VERSION.value: "v"},
            {_MANIFEST.SCHEMA.value: 2, _MANIFEST.INSTALL_ID.value: "test-install-id"},
            persisted_state,
        )
        assert event_line.onboarding_complete is False

    def test_onboarding_complete_at_cutoff_is_false(self):
        persisted_state = _golden_persisted_state()
        event_line = journal_storage_hydration.hydrate_storage_event(
            {_EVENT.EVENT.value: "first_automation_started", _EVENT.TIMESTAMP.value: 1060.0},
            {_CTX.SESSION_ID.value: "s", _CTX.APP_VERSION.value: "v"},
            {_MANIFEST.SCHEMA.value: 2, _MANIFEST.INSTALL_ID.value: "test-install-id"},
            persisted_state,
        )
        assert event_line.onboarding_complete is False

    def test_onboarding_complete_after_cutoff(self):
        persisted_state = _golden_persisted_state()
        event_line = journal_storage_hydration.hydrate_storage_event(
            {_EVENT.EVENT.value: "automation_started", _EVENT.TIMESTAMP.value: 1061.0},
            {_CTX.SESSION_ID.value: "s", _CTX.APP_VERSION.value: "v"},
            {_MANIFEST.SCHEMA.value: 2, _MANIFEST.INSTALL_ID.value: "test-install-id"},
            persisted_state,
        )
        assert event_line.onboarding_complete is True


class TestHydrateMissingData:
    def test_event_before_ctx_uses_empty_session_and_app_version(self):
        persisted_state = journal_state.JournalPersistedState(install_id="install-1")
        event_line = journal_storage_hydration.hydrate_storage_event(
            {_EVENT.EVENT.value: "wallet_setup_succeeded", _EVENT.TIMESTAMP.value: 1.0},
            {},
            {_MANIFEST.SCHEMA.value: 2, _MANIFEST.INSTALL_ID.value: "install-1"},
            persisted_state,
        )
        assert event_line.session_id == ""
        assert event_line.app_version == ""

    def test_recreated_manifest_still_hydrates_events(self, journal_persisted_state):
        journal_directory = journal_state.get_journal_directory()
        os.makedirs(journal_directory, exist_ok=True)
        manifest_path = os.path.join(journal_directory, journal_constants.MANIFEST_FILE_NAME)
        with open(manifest_path, "w", encoding="utf-8") as manifest_file:
            manifest_file.write("{not-json")
        journal_state.ensure_journal_manifest(journal_directory)
        events_path = os.path.join(journal_directory, journal_constants.EVENTS_FILE_NAME)
        with open(events_path, "w", encoding="utf-8") as events_file:
            events_file.write(
                json.dumps(
                    {
                        journal_constants.STORAGE_CTX_KEY: {
                            _CTX.SESSION_ID.value: "session-1",
                            _CTX.APP_VERSION.value: "1.0.0",
                        },
                    },
                )
                + "\n",
            )
            events_file.write(
                json.dumps(
                    {
                        _EVENT.EVENT.value: journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
                        _EVENT.TIMESTAMP.value: 1.0,
                        _EVENT.ATTRIBUTES.value: {"configured": True},
                    },
                )
                + "\n",
            )
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0].install_id == journal_persisted_state.install_id


class TestCtxAppendLifecycle:
    def test_first_append_writes_ctx_and_second_skips_it(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=1.0,
        )
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node"},
            timestamp=2.0,
        )
        segment_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        with open(segment_path, encoding="utf-8") as segment_file:
            lines = [line for line in segment_file.read().splitlines() if line.strip()]
        assert len(lines) == 3
        assert json.loads(lines[0])[journal_constants.STORAGE_CTX_KEY][_CTX.SESSION_ID.value] == (
            journal_state.get_session_id()
        )

    def test_reset_session_id_writes_new_ctx(self, journal_persisted_state):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
            attributes={"configured": True},
            timestamp=1.0,
        )
        journal_state.reset_session_id()
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node"},
            timestamp=2.0,
        )
        segment_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        ctx_lines = []
        with open(segment_path, encoding="utf-8") as segment_file:
            for raw_line in segment_file:
                parsed_line = json.loads(raw_line)
                if journal_constants.STORAGE_CTX_KEY in parsed_line:
                    ctx_lines.append(parsed_line[journal_constants.STORAGE_CTX_KEY][_CTX.SESSION_ID.value])
        assert len(ctx_lines) == 2
        assert ctx_lines[0] != ctx_lines[1]


class TestCtxCapRewrite:
    def test_cap_rewrite_keeps_valid_storage_format(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=2)
        journal_persisted_state.first_automation_started_at = 100.0
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        for event_index in range(3):
            journal_module.record(
                journal_events.NodeJournalEvent.AUTOMATION_STARTED,
                attributes={"automation_id": f"auto-{event_index}"},
                timestamp=200.0 + event_index,
            )

        events_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.EVENTS_FILE_NAME,
        )
        with open(events_path, encoding="utf-8") as events_file:
            lines = [line for line in events_file.read().splitlines() if line.strip()]
        assert any(journal_constants.STORAGE_CTX_KEY in json.loads(line) for line in lines)
        events = journal_module.read_events()
        assert len(events) == 2
        assert events[0].timestamp == 201.0
        assert events[1].timestamp == 202.0

        journal_module.record(
            journal_events.NodeJournalEvent.AUTOMATION_STOPPED,
            attributes={"automation_id": "auto-next"},
            timestamp=300.0,
        )
        with open(events_path, encoding="utf-8") as events_file:
            rewritten_lines = [line for line in events_file.read().splitlines() if line.strip()]
        ctx_line_count = sum(
            1 for line in rewritten_lines if journal_constants.STORAGE_CTX_KEY in json.loads(line)
        )
        assert ctx_line_count == 1


class TestManifestRecreate:
    def test_missing_manifest_is_created(self, journal_persisted_state):
        journal_directory = journal_state.get_journal_directory()
        manifest_path = os.path.join(journal_directory, journal_constants.MANIFEST_FILE_NAME)
        if os.path.isfile(manifest_path):
            os.remove(manifest_path)
        manifest = journal_state.ensure_journal_manifest(journal_directory)
        assert manifest[_MANIFEST.SCHEMA.value] == journal_constants.JOURNAL_SCHEMA_VERSION
        assert manifest[_MANIFEST.INSTALL_ID.value] == journal_persisted_state.install_id
        assert os.path.isfile(manifest_path)


import json
import os

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


def _ctx_line(session_id: str = "session-1", app_version: str = "1.0.0") -> str:
    return json.dumps(
        {
            journal_constants.STORAGE_CTX_KEY: {
                _CTX.SESSION_ID.value: session_id,
                _CTX.APP_VERSION.value: app_version,
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _storage_event_line(*, event_name: str, timestamp: float, attributes: dict | None = None) -> str:
    payload = {_EVENT.EVENT.value: event_name, _EVENT.TIMESTAMP.value: timestamp}
    if attributes is not None:
        payload[_EVENT.ATTRIBUTES.value] = attributes
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _write_events_file(path: str, lines: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    journal_state.ensure_journal_manifest(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as events_file:
        for line in lines:
            events_file.write(line + "\n")


class TestReadEventsJsonlCorruptLines:
    def test_skips_truncated_invalid_and_garbage_lines(self, journal_persisted_state):
        events_path = os.path.join(journal_state.get_journal_directory(), journal_constants.EVENTS_FILE_NAME)
        _write_events_file(
            events_path,
            [
                _ctx_line(),
                _storage_event_line(
                    event_name=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
                    timestamp=1.0,
                    attributes={},
                ),
                '{"event":"node_process_startup_succeeded","timestamp":1',
                json.dumps({_EVENT.TIMESTAMP.value: 2.0, _EVENT.ATTRIBUTES.value: {}}),
                json.dumps({_EVENT.EVENT.value: "wallet_setup_attempt", _EVENT.TIMESTAMP.value: "not-a-float"}),
                "not json at all",
                _storage_event_line(
                    event_name=journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT.value,
                    timestamp=3.0,
                    attributes={},
                ),
            ],
        )

        events = journal_module.read_events()
        assert len(events) == 2
        assert events[0].event == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED
        assert events[1].event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT


class TestReadOnboardingSegmentCorruptLines:
    def test_skips_corrupt_segment_lines_and_keeps_valid_pinned_events(self, journal_persisted_state):
        journal_directory = journal_state.get_journal_directory()
        segment_path = os.path.join(journal_directory, journal_constants.ONBOARDING_SEGMENT_FILE_NAME)
        _write_events_file(
            segment_path,
            [
                _ctx_line(),
                _storage_event_line(
                    event_name=journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT.value,
                    timestamp=10.0,
                    attributes={},
                ),
                "corrupt segment line",
            ],
        )

        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0].event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT
        assert events[0].timestamp == 10.0


class TestCapEvictionWithCorruptTrailingLine:
    def test_enforces_cap_after_skipping_corrupt_line(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=2)
        journal_persisted_state.first_automation_started_at = 0.5
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        events_path = os.path.join(journal_state.get_journal_directory(), journal_constants.EVENTS_FILE_NAME)
        _write_events_file(
            events_path,
            [
                _ctx_line(),
                _storage_event_line(
                    event_name=journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value,
                    timestamp=1.0,
                    attributes={},
                ),
                "truncated-json-line",
                _storage_event_line(
                    event_name=journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT.value,
                    timestamp=2.0,
                    attributes={},
                ),
            ],
        )

        journal_module.record(
            journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
            attributes={"provider": "test"},
            timestamp=3.0,
        )

        events = journal_module.read_events()
        assert len(events) == 2
        assert events[0].timestamp == 2.0
        assert events[1].timestamp == 3.0


import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


class TestJournalCapEviction:
    def test_evicts_post_onboarding_events_before_pre_onboarding_events(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=10)

        journal_persisted_state.first_automation_started_at = 100.0
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        for event_index in range(5):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"protected-{event_index}"},
                timestamp=10.0 + event_index,
            )
        for event_index in range(10):
            journal_module.record(
                journal_events.NodeJournalEvent.AUTOMATION_STARTED,
                attributes={
                    "automation_id": f"auto-{event_index}",
                    "octobot_kind": "default",
                    "flow_subtype": None,
                },
                timestamp=200.0 + event_index,
            )

        events = journal_module.read_events()
        assert len(events) == 10
        protected_timestamps = {event_line.timestamp for event_line in events if event_line.timestamp < 100.0}
        evictable_timestamps = {event_line.timestamp for event_line in events if event_line.timestamp >= 100.0}
        assert protected_timestamps == {10.0, 11.0, 12.0, 13.0, 14.0}
        assert evictable_timestamps == {205.0, 206.0, 207.0, 208.0, 209.0}

    def test_does_not_trim_when_under_cap(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=10)

        for event_index in range(3):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"method-{event_index}"},
                timestamp=float(event_index),
            )

        assert len(journal_module.read_events()) == 3


import json
import os

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


class TestOnboardingSegmentPreserved:
    def test_onboarding_events_written_to_segment_file(self, journal_persisted_state, journal_user_root):
        journal_module.record(
            journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
            attributes={"node_type": "node", "setup_method": "api"},
            timestamp=1.0,
        )
        segment_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        assert os.path.isfile(segment_path)
        with open(segment_path, encoding="utf-8") as segment_file:
            assert "wallet_setup_attempt" in segment_file.read()

    def test_post_onboarding_events_skip_segment_file(self, journal_persisted_state, journal_user_root):
        journal_persisted_state.first_automation_started_at = 50.0
        journal_persisted_state.onboarding_complete = True
        journal_state.save_persisted_state(journal_persisted_state)

        journal_module.record(
            journal_events.NodeJournalEvent.AUTOMATION_STARTED,
            attributes={
                "automation_id": "auto-1",
                "octobot_kind": "default",
                "flow_subtype": None,
            },
            timestamp=60.0,
        )

        segment_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.ONBOARDING_SEGMENT_FILE_NAME,
        )
        assert not os.path.isfile(segment_path)

    def test_segment_events_survive_main_file_cap_eviction(self, journal_persisted_state):
        journal_store.reset_default_store()
        journal_store.get_store(max_events=3)

        for event_index in range(5):
            journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
                attributes={"node_type": "node", "setup_method": f"method-{event_index}"},
                timestamp=float(event_index),
            )

        events = journal_module.read_events()
        setup_methods = [
            event_line.attributes.setup_method
            for event_line in events
            if event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT
        ]
        assert setup_methods == ["method-0", "method-1", "method-2", "method-3", "method-4"]


class TestLegacyJsonlEventRead:
    def test_reads_obsolete_event_name_as_unknown(self, journal_persisted_state, journal_user_root):
        events_path = os.path.join(
            journal_state.get_journal_directory(),
            journal_constants.EVENTS_FILE_NAME,
        )
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        journal_state.ensure_journal_manifest(os.path.dirname(events_path))
        with open(events_path, "w", encoding="utf-8") as events_file:
            events_file.write(
                json.dumps(
                    {
                        journal_constants.STORAGE_CTX_KEY: {
                            _CTX.SESSION_ID.value: "session-1",
                            _CTX.APP_VERSION.value: "1.0.0",
                        },
                    },
                )
                + "\n",
            )
            events_file.write(
                json.dumps(
                    {
                        _EVENT.EVENT.value: "legacy_custom_event",
                        _EVENT.TIMESTAMP.value: 12.0,
                        _EVENT.ATTRIBUTES.value: {},
                    },
                )
                + "\n",
            )
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.UNKNOWN
        assert event_line.attributes.raw_event_name == "legacy_custom_event"
