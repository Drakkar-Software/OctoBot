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

import dataclasses
import json
import logging
import os
import threading

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.storage_hydration as journal_storage_hydration
import octobot.community.node_journal.state as journal_state

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _FileWriteState:
    last_ctx: dict | None = None


class JournalStore:
    def __init__(
        self,
        *,
        max_events: int = journal_constants.JOURNAL_MAX_EVENTS,
        journal_directory: str | None = None,
    ) -> None:
        self._max_events = max_events
        self._journal_directory = journal_directory or journal_state.get_journal_directory()
        self._events_path = os.path.join(self._journal_directory, journal_constants.EVENTS_FILE_NAME)
        self._onboarding_path = os.path.join(
            self._journal_directory, journal_constants.ONBOARDING_SEGMENT_FILE_NAME
        )
        self._lock = threading.Lock()
        self._file_write_states: dict[str, _FileWriteState] = {}
        os.makedirs(self._journal_directory, exist_ok=True)
        journal_state.ensure_journal_manifest(self._journal_directory)

    def append(self, event_line: journal_models.JournalEventLine, *, is_onboarding_segment: bool) -> None:
        journal_module.run_journal_operation(
            "store.append",
            lambda: self._append(event_line, is_onboarding_segment=is_onboarding_segment),
            default=None,
        )

    def read_all_events(self) -> list[journal_models.JournalEventLine]:
        return journal_module.run_journal_operation(
            "store.read_all_events",
            self._read_all_events,
            default=[],
        )

    def _append(self, event_line: journal_models.JournalEventLine, *, is_onboarding_segment: bool) -> None:
        journal_state.ensure_journal_manifest(self._journal_directory)
        with self._lock:
            if is_onboarding_segment:
                self._append_to_file(self._onboarding_path, event_line)
            else:
                self._append_to_file(self._events_path, event_line)
                self._enforce_cap()

    def _read_all_events(self) -> list[journal_models.JournalEventLine]:
        manifest = journal_state.ensure_journal_manifest(self._journal_directory)
        with self._lock:
            pinned_onboarding = self._parse_jsonl_file(self._onboarding_path, manifest=manifest)
            main_events = self._parse_jsonl_file(self._events_path, manifest=manifest)
        if not pinned_onboarding:
            return main_events
        merged_by_key = {}
        for event_line in pinned_onboarding + main_events:
            merged_by_key[self._event_dedup_key(event_line)] = event_line
        return sorted(merged_by_key.values(), key=lambda line: line.timestamp)

    def _enforce_cap(self) -> None:
        manifest = journal_state.ensure_journal_manifest(self._journal_directory)
        main_events = self._parse_jsonl_file(self._events_path, manifest=manifest)
        if len(main_events) <= self._max_events:
            return
        persisted_state = journal_state.load_persisted_state()
        onboarding_cutoff = persisted_state.first_automation_started_at
        protected_events = []
        evictable_events = []
        for event_line in main_events:
            if onboarding_cutoff is None or event_line.timestamp <= onboarding_cutoff:
                protected_events.append(event_line)
            else:
                evictable_events.append(event_line)
        overflow = len(main_events) - self._max_events
        if overflow <= 0:
            return
        if len(evictable_events) >= overflow:
            kept_evictable = evictable_events[overflow:]
        else:
            kept_evictable = []
            protected_overflow = overflow - len(evictable_events)
            protected_events = protected_events[protected_overflow:]
        kept_events = protected_events + kept_evictable
        self._write_jsonl_file(self._events_path, kept_events)

    def _get_write_state(self, path: str) -> _FileWriteState:
        if path not in self._file_write_states:
            self._file_write_states[path] = _FileWriteState()
        return self._file_write_states[path]

    def _current_ctx(self) -> dict[str, str]:
        context_field = journal_enums.JournalStorageContextField
        return {
            context_field.SESSION_ID.value: journal_state.get_session_id(),
            context_field.APP_VERSION.value: octobot_constants.LONG_VERSION,
        }

    def _should_write_ctx(self, path: str, current_ctx: dict[str, str], write_state: _FileWriteState) -> bool:
        context_field = journal_enums.JournalStorageContextField
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return True
        if write_state.last_ctx is None:
            return True
        return (
            write_state.last_ctx.get(context_field.SESSION_ID.value) != current_ctx[context_field.SESSION_ID.value]
            or write_state.last_ctx.get(context_field.APP_VERSION.value) != current_ctx[context_field.APP_VERSION.value]
        )

    def _append_to_file(self, path: str, event_line: journal_models.JournalEventLine) -> None:
        current_ctx = self._current_ctx()
        write_state = self._get_write_state(path)
        lines_to_write = []
        if self._should_write_ctx(path, current_ctx, write_state):
            lines_to_write.append(self._serialize_ctx_line(current_ctx))
        lines_to_write.append(json.dumps(event_line.to_storage_dict(), separators=(",", ":"), sort_keys=True))
        with open(path, "a", encoding="utf-8") as jsonl_file:
            for serialized_line in lines_to_write:
                jsonl_file.write(serialized_line + "\n")
        write_state.last_ctx = current_ctx

    @staticmethod
    def _serialize_ctx_line(ctx: dict[str, str]) -> str:
        return json.dumps(
            {journal_constants.STORAGE_CTX_KEY: ctx},
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _event_dedup_key(event_line: journal_models.JournalEventLine) -> tuple:
        return (
            event_line.timestamp,
            event_line.event.value,
            event_line.session_id,
            json.dumps(event_line.attributes.to_dict(), sort_keys=True),
        )

    def _parse_jsonl_file(
        self,
        path: str,
        *,
        manifest: dict,
    ) -> list[journal_models.JournalEventLine]:
        if not os.path.isfile(path):
            return []
        persisted_state = journal_state.load_persisted_state()
        parsed_lines = []
        running_ctx: dict = {}
        missing_data_warnings: set[str] = set()
        with open(path, encoding="utf-8") as jsonl_file:
            for line_number, raw_line in enumerate(jsonl_file, start=1):
                stripped_line = raw_line.strip()
                if not stripped_line:
                    continue
                try:
                    parsed_line = json.loads(stripped_line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "Skipping invalid journal line %s:%s (%s: %s)",
                        path,
                        line_number,
                        type(exc).__name__,
                        exc,
                    )
                    continue
                if journal_constants.STORAGE_CTX_KEY in parsed_line:
                    ctx_payload = parsed_line[journal_constants.STORAGE_CTX_KEY]
                    if isinstance(ctx_payload, dict):
                        running_ctx = ctx_payload
                    else:
                        logger.warning(
                            "Skipping invalid journal context line %s:%s",
                            path,
                            line_number,
                        )
                    continue
                if journal_enums.JournalEventLineField.EVENT.value not in parsed_line:
                    logger.warning(
                        "Skipping unrecognized journal line %s:%s",
                        path,
                        line_number,
                    )
                    continue
                try:
                    parsed_lines.append(
                        journal_storage_hydration.hydrate_storage_event(
                            parsed_line,
                            running_ctx,
                            manifest,
                            persisted_state,
                            missing_data_warnings=missing_data_warnings,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Skipping invalid journal line %s:%s (%s: %s)",
                        path,
                        line_number,
                        type(exc).__name__,
                        exc,
                    )
        return parsed_lines

    def _write_jsonl_file(self, path: str, events: list[journal_models.JournalEventLine]) -> None:
        write_state = self._get_write_state(path)
        if not events:
            with open(path, "w", encoding="utf-8"):
                pass
            write_state.last_ctx = None
            return

        grouped_lines: list[str] = []
        current_group_key: tuple[str, str] | None = None
        current_group_events: list[journal_models.JournalEventLine] = []
        for event_line in events:
            group_key = (event_line.session_id, event_line.app_version)
            if group_key != current_group_key:
                if current_group_events and current_group_key is not None:
                    grouped_lines.extend(
                        self._serialize_event_group(current_group_key, current_group_events)
                    )
                current_group_key = group_key
                current_group_events = [event_line]
            else:
                current_group_events.append(event_line)
        if current_group_events and current_group_key is not None:
            grouped_lines.extend(self._serialize_event_group(current_group_key, current_group_events))

        with open(path, "w", encoding="utf-8") as jsonl_file:
            jsonl_file.write("\n".join(grouped_lines) + "\n")

        if current_group_key is not None:
            last_session_id, last_app_version = current_group_key
            context_field = journal_enums.JournalStorageContextField
            write_state.last_ctx = {
                context_field.SESSION_ID.value: last_session_id,
                context_field.APP_VERSION.value: last_app_version,
            }

    def _serialize_event_group(
        self,
        group_key: tuple[str, str],
        group_events: list[journal_models.JournalEventLine],
    ) -> list[str]:
        session_id, app_version = group_key
        context_field = journal_enums.JournalStorageContextField
        serialized_lines = [
            self._serialize_ctx_line({
                context_field.SESSION_ID.value: session_id,
                context_field.APP_VERSION.value: app_version,
            }),
        ]
        for event_line in group_events:
            serialized_lines.append(
                json.dumps(event_line.to_storage_dict(), separators=(",", ":"), sort_keys=True)
            )
        return serialized_lines


_default_store: JournalStore | None = None


def get_store(*, max_events: int | None = None) -> JournalStore:
    global _default_store
    if _default_store is None or (max_events is not None and _default_store._max_events != max_events):
        kwargs = {}
        if max_events is not None:
            kwargs["max_events"] = max_events
        _default_store = JournalStore(**kwargs)
    return _default_store


def reset_default_store() -> None:
    global _default_store
    _default_store = None
