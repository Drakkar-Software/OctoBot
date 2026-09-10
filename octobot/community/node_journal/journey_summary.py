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

import collections
import time
import typing

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.state as journal_state

_MILESTONE_LABELS = {
    journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED: "wallet_setup",
    journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED: "external_connect",
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATED: "account_validated",
    journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED: "strategy_create",
    journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED: "strategy_edit",
    journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED: "first_automation",
}

_SUCCESS_EVENTS = frozenset({
    journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
    journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
    journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATED,
    journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
    journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
    journal_events.NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
})


def build_journey_summary(events: list[dict]) -> dict:
    persisted_state = journal_state.load_persisted_state()
    install_start = persisted_state.onboarding_started_at
    parsed_events = _parse_events(events)
    onboarding_complete = any(
        event == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED for event, _ in parsed_events
    )
    furthest_step_reached = _get_furthest_step(parsed_events)
    last_successful_step = _get_last_successful_step(parsed_events)
    first_failure = _get_first_failure(parsed_events)
    retry_counts = _get_retry_counts(parsed_events)
    step_durations_seconds = _get_step_durations(parsed_events, install_start)
    step_deltas_seconds = _get_step_deltas(step_durations_seconds)
    external_stats = _get_external_connect_stats(parsed_events)
    return {
        "onboarding_complete": onboarding_complete,
        "furthest_step_reached": furthest_step_reached,
        "last_successful_step": last_successful_step,
        "first_failure": first_failure,
        "retry_counts": retry_counts,
        "step_durations_seconds": step_durations_seconds,
        "step_deltas_seconds": step_deltas_seconds,
        **external_stats,
    }


def _parse_events(events: list[dict]) -> list[tuple[journal_events.NodeJournalEvent | None, dict]]:
    parsed_events = []
    for event_line in events:
        try:
            parsed_events.append((journal_events.NodeJournalEvent(event_line["event"]), event_line))
        except ValueError:
            parsed_events.append((None, event_line))
    return parsed_events


def _get_furthest_step(parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]]) -> str | None:
    best_rank = -1
    best_event_name = None
    for event, _ in parsed_events:
        if event is None:
            continue
        rank = journal_events.FUNNEL_STEP_RANK.get(event)
        if rank is not None and rank >= best_rank:
            best_rank = rank
            best_event_name = event.value
    return best_event_name


def _get_last_successful_step(parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]]) -> str | None:
    last_success = None
    for event, _ in parsed_events:
        if event in _SUCCESS_EVENTS:
            last_success = event.value
    return last_success


def _get_first_failure(parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]]) -> dict | None:
    for event, event_line in parsed_events:
        if event is None or event not in journal_events.FAILURE_EVENTS:
            continue
        attributes = event_line.get("attributes", {})
        return {
            "event": event.value,
            "timestamp": event_line.get("timestamp"),
            "error_category": attributes.get("error_category"),
            "error_message": attributes.get("error_message"),
        }
    return None


def _get_retry_counts(parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]]) -> dict[str, int]:
    retry_counts: dict[str, int] = collections.Counter()
    for event, _ in parsed_events:
        if event is not None and event in journal_events.FAILURE_EVENTS:
            retry_counts[event.value] += 1
    return dict(retry_counts)


def _get_step_durations(
    parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]],
    install_start: float | None,
) -> dict[str, float]:
    if install_start is None:
        return {}
    step_durations: dict[str, float] = {}
    for event, event_line in parsed_events:
        label = _MILESTONE_LABELS.get(event) if event is not None else None
        if label is None:
            continue
        event_timestamp = float(event_line.get("timestamp", install_start))
        step_durations[label] = round(max(0.0, event_timestamp - install_start), 3)
    return step_durations


def _get_step_deltas(step_durations_seconds: dict[str, float]) -> dict[str, float]:
    ordered_labels = [
        "wallet_setup",
        "external_connect",
        "account_validated",
        "strategy_create",
        "strategy_edit",
        "first_automation",
    ]
    deltas: dict[str, float] = {}
    previous_label = None
    previous_duration = None
    for label in ordered_labels:
        current_duration = step_durations_seconds.get(label)
        if current_duration is None:
            continue
        if previous_label is not None and previous_duration is not None:
            delta_key = f"{previous_label}_to_{label}"
            deltas[delta_key] = round(max(0.0, current_duration - previous_duration), 3)
        previous_label = label
        previous_duration = current_duration
    return deltas


def _get_external_connect_stats(parsed_events: list[tuple[journal_events.NodeJournalEvent | None, dict]]) -> dict:
    connect_events = [
        event_line
        for event, event_line in parsed_events
        if event == journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED
    ]
    if not connect_events:
        return {
            "external_connect_count": 0,
            "first_external_connect_at": None,
            "last_external_connect_at": None,
            "longest_connect_gap_seconds": None,
        }
    timestamps = [float(event_line.get("timestamp", 0)) for event_line in connect_events]
    prior_gaps = [
        float(event_line.get("attributes", {}).get("prior_gap_seconds"))
        for event_line in connect_events
        if event_line.get("attributes", {}).get("prior_gap_seconds") is not None
    ]
    return {
        "external_connect_count": len(connect_events),
        "first_external_connect_at": min(timestamps),
        "last_external_connect_at": max(timestamps),
        "longest_connect_gap_seconds": max(prior_gaps) if prior_gaps else None,
    }


def build_upload_envelope(events: list[dict], *, app_version: str, note: str | None = None) -> dict:
    persisted_state = journal_state.load_persisted_state()
    journey_summary = build_journey_summary(events)
    envelope = {
        "install_id": persisted_state.install_id,
        "app_version": app_version,
        "onboarding_started_at": persisted_state.onboarding_started_at,
        "onboarding_complete": journey_summary.get("onboarding_complete", False),
        "journey_summary": journey_summary,
        "events": events,
        "uploaded": False,
        "ready": True,
        "event_count": len(events),
    }
    if note:
        envelope["note"] = note
    return envelope
