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

import octobot_commons.dataclasses as commons_dataclasses

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events


@dataclasses.dataclass
class _NodeJournalMinimizableDataclass(commons_dataclasses.MinimizableDataclass):
    def to_dict(self, include_default_values: bool = False) -> dict:
        return super().to_dict(include_default_values=include_default_values)


@dataclasses.dataclass
class JournalEventAttributes(_NodeJournalMinimizableDataclass):
    account_count: int | None = None
    account_id: str | None = None
    account_ids: list[str] | None = None
    account_state: str | None = None
    action_type: str | None = None
    automation_count: int | None = None
    automation_id: str | None = None
    running_automation_count: int | None = None
    backend: str | None = None
    cancel_orders: bool | None = None
    collection: str | None = None
    configured: bool | None = None
    configuration_type: str | None = None
    connection_sequence: int | None = None
    duration_since_install_start: float | None = None
    error_category: str | None = None
    error_message: str | None = None
    error_origin: str | None = None
    error_status: str | None = None
    exchange_name: str | None = None
    failure_reason: str | None = None
    flow_subtype: str | None = None
    force_exit: bool | None = None
    http_status: int | None = None
    init_phase: str | None = None
    is_reconnect: bool | None = None
    is_simulated: bool | None = None
    new_install: bool | None = None
    node_type: str | None = None
    octobot_kind: str | None = None
    operation: str | None = None
    prior_gap_seconds: float | None = None
    provider: str | None = None
    reconciled: bool | None = None
    recovery_action: str | None = None
    refreshed_count: int | None = None
    retriable: bool | None = None
    raw_event_name: str | None = None
    setup_method: str | None = None
    source: str | None = None
    startup_phase: str | None = None
    strategy_id: str | None = None
    sync_session_id: str | None = None
    user_action_id: str | None = None
    wallet_configured: bool | None = None

    @classmethod
    def merge(cls, base: "JournalEventAttributes | None", overrides: dict | None) -> "JournalEventAttributes":
        merged = dataclasses.asdict(base) if base is not None else {}
        if overrides:
            known_fields = cls.get_field_names()
            for raw_key, value in overrides.items():
                if raw_key in known_fields:
                    merged[raw_key] = value
        return cls(**merged)


@dataclasses.dataclass
class JournalEventLine(_NodeJournalMinimizableDataclass):
    event: journal_events.NodeJournalEvent
    timestamp: float
    session_id: str
    install_id: str
    app_version: str
    distribution: str
    onboarding_complete: bool
    attributes: JournalEventAttributes
    recorded: bool = True

    def to_dict(self, include_default_values: bool = False) -> dict:
        serialized = super().to_dict(include_default_values=include_default_values)
        event_line_field = journal_enums.JournalEventLineField
        serialized[event_line_field.EVENT.value] = self.event.value
        if self.attributes is not None:
            serialized[event_line_field.ATTRIBUTES.value] = self.attributes.to_dict(
                include_default_values=include_default_values,
            )
        else:
            serialized[event_line_field.ATTRIBUTES.value] = {}
        if not self.recorded:
            serialized[event_line_field.RECORDED.value] = False
        elif not include_default_values and serialized.get(event_line_field.RECORDED.value) is True:
            serialized.pop(event_line_field.RECORDED.value, None)
        return serialized

    def to_storage_dict(self) -> dict:
        event_line_field = journal_enums.JournalEventLineField
        serialized = {
            event_line_field.EVENT.value: self.event.value,
            event_line_field.TIMESTAMP.value: self.timestamp,
        }
        if self.attributes is not None:
            attributes_dict = self.attributes.to_dict()
            if attributes_dict:
                serialized[event_line_field.ATTRIBUTES.value] = attributes_dict
        if not self.recorded:
            serialized[event_line_field.RECORDED.value] = False
        return serialized

    @classmethod
    def from_dict(cls, event_line: dict) -> "JournalEventLine":
        event_line_field = journal_enums.JournalEventLineField
        parsed_event, coerced_raw_event_name = journal_events.coerce_node_journal_event(
            event_line[event_line_field.EVENT.value],
        )
        attributes = JournalEventAttributes.from_dict(event_line.get(event_line_field.ATTRIBUTES.value))
        if attributes is None:
            attributes = JournalEventAttributes()
        if coerced_raw_event_name is not None:
            attributes = JournalEventAttributes.merge(
                attributes,
                {"raw_event_name": coerced_raw_event_name},
            )
        return cls(
            event=parsed_event,
            timestamp=float(event_line[event_line_field.TIMESTAMP.value]),
            session_id=str(event_line.get(event_line_field.SESSION_ID.value, "")),
            install_id=str(event_line.get(event_line_field.INSTALL_ID.value, "")),
            app_version=str(event_line.get(event_line_field.APP_VERSION.value, "")),
            distribution=str(event_line.get(event_line_field.DISTRIBUTION.value, "")),
            onboarding_complete=bool(event_line.get(event_line_field.ONBOARDING_COMPLETE.value, False)),
            attributes=attributes,
            recorded=event_line.get(event_line_field.RECORDED.value, True),
        )


@dataclasses.dataclass
class FirstFailureInfo(_NodeJournalMinimizableDataclass):
    event: str
    timestamp: float | None
    error_category: str | None
    error_message: str | None

    @classmethod
    def from_dict(cls, payload: dict | None) -> "FirstFailureInfo | None":
        if payload is None:
            return None
        return super().from_dict(payload)


@dataclasses.dataclass
class JourneySummary(_NodeJournalMinimizableDataclass):
    onboarding_complete: bool
    furthest_step_reached: str | None
    last_successful_step: str | None
    first_failure: FirstFailureInfo | None
    retry_counts: dict[str, int]
    step_durations_seconds: dict[str, float]
    step_deltas_seconds: dict[str, float]
    external_connect_count: int
    first_external_connect_at: float | None
    last_external_connect_at: float | None
    longest_connect_gap_seconds: float | None
    ui_blocking_issues_count: int = 0


@dataclasses.dataclass
class UploadEnvelope(_NodeJournalMinimizableDataclass):
    install_id: str
    app_version: str
    onboarding_started_at: float | None
    onboarding_complete: bool
    journey_summary: JourneySummary
    events: list[JournalEventLine]
    uploaded: bool
    ready: bool
    event_count: int
    note: str | None = None

    def to_dict(self, include_default_values: bool = False) -> dict:
        serialized = super().to_dict(include_default_values=include_default_values)
        serialized["events"] = [event_line.to_storage_dict() for event_line in self.events]
        serialized["journey_summary"] = self.journey_summary.to_dict(
            include_default_values=include_default_values,
        )
        return serialized
