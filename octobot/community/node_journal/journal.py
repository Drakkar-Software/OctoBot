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

"""Core write/read pipeline for the node journal."""

import logging
import os
import time
import typing

import octobot.constants as octobot_constants

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store

logger = logging.getLogger(__name__)

_DISABLED_VALUES = frozenset({"0", "false", "no", "off"})


def is_journal_enabled() -> bool:
    raw_value = os.environ.get(journal_constants.JOURNAL_ENABLED_ENV_VAR)
    if raw_value is None:
        return True
    return raw_value.strip().lower() not in _DISABLED_VALUES


def run_journal_operation(
    operation_name: str,
    operation: typing.Callable[[], typing.Any],
    *,
    default: typing.Any,
) -> typing.Any:
    try:
        return operation()
    except Exception as exc:
        logger.exception("Journal %s failed: %s", operation_name, exc)
        return default


def sanitize_attribute_value(value: typing.Any) -> typing.Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, list):
        return value
    return str(value)


def sanitize_event_attributes(
    event: journal_events.NodeJournalEvent,
    attributes: journal_models.JournalEventAttributes,
) -> journal_models.JournalEventAttributes:
    sanitized_attributes = {}
    for field_name, value in attributes.to_dict().items():
        if value is None:
            continue
        sanitized_attributes[field_name] = sanitize_attribute_value(value)
    return journal_models.JournalEventAttributes.from_dict(sanitized_attributes)


def record(
    event: journal_events.NodeJournalEvent | str,
    *,
    attributes: journal_models.JournalEventAttributes | dict | None = None,
    timestamp: float | None = None,
) -> journal_models.JournalEventLine:
    return run_journal_operation(
        "record",
        lambda: _record(event, attributes=attributes, timestamp=timestamp),
        default=_build_disabled_event_stub_for_input(event, attributes),
    )


def read_events() -> list[journal_models.JournalEventLine]:
    if not is_journal_enabled():
        return []
    return journal_store.get_store().read_all_events()


def initialize_for_config(config) -> None:
    if not is_journal_enabled():
        return
    journal_state.bind_config(config)
    journal_state.load_persisted_state(config)


def record_failure(
    event: journal_events.NodeJournalEvent,
    *,
    error: BaseException | None = None,
    error_message: str | None = None,
    error_category: str | None = None,
    attributes: journal_models.JournalEventAttributes | dict | None = None,
) -> journal_models.JournalEventLine:
    failure_attributes = journal_models.JournalEventAttributes.merge(
        _coerce_attributes(attributes),
        {},
    )
    if error_category is None and error is not None:
        failure_attributes.error_category = error.__class__.__name__
    elif error_category is not None:
        failure_attributes.error_category = error_category
    if error_message is not None:
        failure_attributes.error_message = error_message
    return record(event, attributes=failure_attributes)


def _record(
    event: journal_events.NodeJournalEvent | str,
    *,
    attributes: journal_models.JournalEventAttributes | dict | None,
    timestamp: float | None,
) -> journal_models.JournalEventLine:
    parsed_event, raw_event_name = journal_events.coerce_node_journal_event(event)
    coerced_attributes = _merge_raw_event_name(_coerce_attributes(attributes), raw_event_name)
    if parsed_event == journal_events.NodeJournalEvent.UNKNOWN:
        logger.error("Unknown journal event: %s", raw_event_name or event)
        return _build_disabled_event_stub(parsed_event, coerced_attributes, recorded=False)
    if not is_journal_enabled():
        return _build_disabled_event_stub(parsed_event, coerced_attributes)
    sanitized_attributes = sanitize_event_attributes(parsed_event, coerced_attributes)
    if (
        parsed_event in journal_events.FAILURE_EVENTS
        and sanitized_attributes.error_category is None
    ):
        logger.error("%s requires error_category", parsed_event.value)
        return _build_disabled_event_stub(parsed_event, sanitized_attributes, recorded=False)
    emit_timestamp = time.time() if timestamp is None else timestamp
    persisted_state = journal_state.load_persisted_state()
    event_line = journal_models.JournalEventLine(
        event=parsed_event,
        timestamp=emit_timestamp,
        session_id=journal_state.get_session_id(),
        install_id=persisted_state.install_id,
        app_version=octobot_constants.LONG_VERSION,
        distribution=journal_constants.DISTRIBUTION_NODE,
        onboarding_complete=persisted_state.onboarding_complete,
        attributes=sanitized_attributes,
    )
    is_onboarding_segment = not persisted_state.onboarding_complete
    journal_store.get_store().append(event_line, is_onboarding_segment=is_onboarding_segment)
    if parsed_event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED:
        journal_state.mark_first_automation_started(emit_timestamp)
    return event_line


def _coerce_attributes(
    attributes: journal_models.JournalEventAttributes | dict | None,
) -> journal_models.JournalEventAttributes:
    if attributes is None:
        return journal_models.JournalEventAttributes()
    if isinstance(attributes, journal_models.JournalEventAttributes):
        return attributes
    return journal_models.JournalEventAttributes.from_dict(attributes)


def _merge_raw_event_name(
    attributes: journal_models.JournalEventAttributes,
    raw_event_name: str | None,
) -> journal_models.JournalEventAttributes:
    if raw_event_name is None:
        return attributes
    return journal_models.JournalEventAttributes.merge(
        attributes,
        {"raw_event_name": raw_event_name},
    )


def _build_disabled_event_stub_for_input(
    event: journal_events.NodeJournalEvent | str,
    attributes: journal_models.JournalEventAttributes | dict | None,
    *,
    recorded: bool = False,
) -> journal_models.JournalEventLine:
    parsed_event, raw_event_name = journal_events.coerce_node_journal_event(event)
    coerced_attributes = _merge_raw_event_name(_coerce_attributes(attributes), raw_event_name)
    return _build_disabled_event_stub(parsed_event, coerced_attributes, recorded=recorded)


def _build_disabled_event_stub(
    parsed_event: journal_events.NodeJournalEvent,
    attributes: journal_models.JournalEventAttributes,
    *,
    recorded: bool = False,
) -> journal_models.JournalEventLine:
    return journal_models.JournalEventLine(
        event=parsed_event,
        timestamp=time.time(),
        session_id="",
        install_id="",
        app_version=octobot_constants.LONG_VERSION,
        distribution=journal_constants.DISTRIBUTION_NODE,
        onboarding_complete=False,
        attributes=attributes,
        recorded=recorded,
    )
