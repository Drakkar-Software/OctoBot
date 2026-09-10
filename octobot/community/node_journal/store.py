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
import logging
import os
import threading

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.safe as journal_safe
import octobot.community.node_journal.state as journal_state

logger = logging.getLogger(__name__)


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
        os.makedirs(self._journal_directory, exist_ok=True)

    def append(self, event_line: journal_models.JournalEventLine, *, is_onboarding_segment: bool) -> None:
        journal_safe.run_journal_operation(
            "store.append",
            lambda: self._append(event_line, is_onboarding_segment=is_onboarding_segment),
            default=None,
        )

    def read_all_events(self) -> list[journal_models.JournalEventLine]:
        return journal_safe.run_journal_operation(
            "store.read_all_events",
            self._read_all_events,
            default=[],
        )

    def _append(self, event_line: journal_models.JournalEventLine, *, is_onboarding_segment: bool) -> None:
        serialized = json.dumps(event_line.to_dict(), separators=(",", ":"), sort_keys=True)
        with self._lock:
            with open(self._events_path, "a", encoding="utf-8") as events_file:
                events_file.write(serialized + "\n")
            if is_onboarding_segment:
                with open(self._onboarding_path, "a", encoding="utf-8") as onboarding_file:
                    onboarding_file.write(serialized + "\n")
            self._enforce_cap(is_onboarding_segment=is_onboarding_segment)

    def _read_all_events(self) -> list[journal_models.JournalEventLine]:
        with self._lock:
            pinned_onboarding = self._read_jsonl_file(self._onboarding_path)
            main_events = self._read_jsonl_file(self._events_path)
        if not pinned_onboarding:
            return main_events
        merged_by_key = {}
        for event_line in pinned_onboarding + main_events:
            merged_by_key[self._event_dedup_key(event_line)] = event_line
        return sorted(merged_by_key.values(), key=lambda line: line.timestamp)

    def _enforce_cap(self, *, is_onboarding_segment: bool) -> None:
        del is_onboarding_segment
        main_events = self._read_jsonl_file(self._events_path)
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

    @staticmethod
    def _event_dedup_key(event_line: journal_models.JournalEventLine) -> tuple:
        return (
            event_line.timestamp,
            event_line.event.value,
            event_line.session_id,
            json.dumps(event_line.attributes.to_dict(), sort_keys=True),
        )

    @staticmethod
    def _read_jsonl_file(path: str) -> list[journal_models.JournalEventLine]:
        if not os.path.isfile(path):
            return []
        parsed_lines = []
        with open(path, encoding="utf-8") as jsonl_file:
            for raw_line in jsonl_file:
                stripped_line = raw_line.strip()
                if not stripped_line:
                    continue
                try:
                    parsed_lines.append(journal_models.JournalEventLine.from_dict(json.loads(stripped_line)))
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    logger.exception("Failed to parse journal line in %s: %s", path, exc)
        return parsed_lines

    @staticmethod
    def _write_jsonl_file(path: str, events: list[journal_models.JournalEventLine]) -> None:
        with open(path, "w", encoding="utf-8") as jsonl_file:
            for event_line in events:
                jsonl_file.write(json.dumps(event_line.to_dict(), separators=(",", ":"), sort_keys=True) + "\n")


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
