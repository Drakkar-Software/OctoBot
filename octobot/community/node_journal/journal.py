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

import time

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enabled as journal_enabled
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.sanitize as journal_sanitize
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store


def record(
    event: journal_events.NodeJournalEvent | str,
    *,
    attributes: dict | None = None,
    timestamp: float | None = None,
) -> dict:
    event_name = event.value if isinstance(event, journal_events.NodeJournalEvent) else str(event)
    if event_name not in journal_events.NodeJournalEvent._value2member_map_:
        raise ValueError(f"Unknown journal event: {event_name}")
    parsed_event = journal_events.NodeJournalEvent(event_name)
    if not journal_enabled.is_journal_enabled():
        return _build_disabled_event_stub(parsed_event, attributes or {})
    sanitized_attributes = _sanitize_attributes(parsed_event, attributes or {})
    emit_timestamp = time.time() if timestamp is None else timestamp
    persisted_state = journal_state.load_persisted_state()
    event_line = {
        "event": parsed_event.value,
        "timestamp": emit_timestamp,
        "session_id": journal_state.get_session_id(),
        "install_id": persisted_state.install_id,
        "app_version": octobot_constants.LONG_VERSION,
        "distribution": journal_constants.DISTRIBUTION_NODE,
        "onboarding_complete": persisted_state.onboarding_complete,
        "attributes": sanitized_attributes,
    }
    is_onboarding_segment = not persisted_state.onboarding_complete
    journal_store.get_store().append(event_line, is_onboarding_segment=is_onboarding_segment)
    if parsed_event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED:
        journal_state.mark_first_automation_started(emit_timestamp)
    return event_line


def read_events() -> list[dict]:
    if not journal_enabled.is_journal_enabled():
        return []
    return journal_store.get_store().read_all_events()


def initialize_for_config(config) -> None:
    if not journal_enabled.is_journal_enabled():
        return
    journal_state.bind_config(config)
    journal_state.load_persisted_state(config)


def is_journal_enabled() -> bool:
    return journal_enabled.is_journal_enabled()


def _build_disabled_event_stub(
    parsed_event: journal_events.NodeJournalEvent,
    attributes: dict,
) -> dict:
    return {
        "event": parsed_event.value,
        "timestamp": time.time(),
        "session_id": "",
        "install_id": "",
        "app_version": octobot_constants.LONG_VERSION,
        "distribution": journal_constants.DISTRIBUTION_NODE,
        "onboarding_complete": False,
        "attributes": attributes,
        "recorded": False,
    }


def _sanitize_attributes(event: journal_events.NodeJournalEvent, attributes: dict) -> dict:
    sanitized = {}
    for key, value in attributes.items():
        if value is None:
            continue
        if key == "error_message" and isinstance(value, str):
            sanitized[key] = journal_sanitize.sanitize_error_message(value)
        elif isinstance(value, bool):
            sanitized[key] = value
        elif isinstance(value, (int, float, str)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    if event in journal_events.FAILURE_EVENTS:
        if "error_category" not in sanitized:
            raise ValueError(f"{event.value} requires error_category")
        if "error_message" not in sanitized:
            sanitized["error_message"] = ""
    return sanitized


def record_failure(
    event: journal_events.NodeJournalEvent,
    *,
    error: BaseException | None = None,
    error_message: str | None = None,
    error_category: str | None = None,
    attributes: dict | None = None,
) -> dict:
    failure_attributes = dict(attributes or {})
    if error_category is None and error is not None:
        failure_attributes["error_category"] = error.__class__.__name__
    elif error_category is not None:
        failure_attributes["error_category"] = error_category
    if error_message is None and error is not None:
        failure_attributes["error_message"] = str(error)
    elif error_message is not None:
        failure_attributes["error_message"] = error_message
    return record(event, attributes=failure_attributes)
