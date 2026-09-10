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
from pathlib import Path

import octobot.constants as octobot_constants

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journey_summary as journey_summary_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state


_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_golden_events() -> list[journal_models.JournalEventLine]:
    fixture_path = _FIXTURES_DIR / "journey_events.jsonl"
    events = []
    with open(fixture_path, encoding="utf-8") as fixture_file:
        for raw_line in fixture_file:
            stripped_line = raw_line.strip()
            if stripped_line:
                events.append(journal_models.JournalEventLine.from_dict(json.loads(stripped_line)))
    return events


class TestBuildJourneySummary:
    def test_matches_golden_fixture_summary(self, journal_persisted_state):
        journal_persisted_state.onboarding_started_at = 1_000.0
        journal_state.save_persisted_state(journal_persisted_state)

        summary = journey_summary_module.build_journey_summary(_load_golden_events())

        assert summary.onboarding_complete is True
        assert summary.furthest_step_reached == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED.value
        assert summary.last_successful_step == journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED.value
        assert summary.first_failure is not None
        assert summary.first_failure.event == journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED.value
        assert summary.retry_counts == {
            journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED.value: 1,
        }
        assert summary.step_durations_seconds == {
            "wallet_setup": 10.0,
            "external_connect": 30.0,
            "account_validated": 40.0,
            "strategy_create": 50.0,
            "first_automation": 60.0,
        }
        assert summary.step_deltas_seconds == {
            "wallet_setup_to_external_connect": 20.0,
            "external_connect_to_account_validated": 10.0,
            "account_validated_to_strategy_create": 10.0,
            "strategy_create_to_first_automation": 10.0,
        }
        assert summary.external_connect_count == 2
        assert summary.first_external_connect_at == 1_020.0
        assert summary.last_external_connect_at == 1_030.0
        assert summary.longest_connect_gap_seconds == 5.0

    def test_empty_events_returns_minimal_summary(self, journal_persisted_state):
        summary = journey_summary_module.build_journey_summary([])
        assert summary.onboarding_complete is False
        assert summary.furthest_step_reached is None
        assert summary.first_failure is None
        assert summary.external_connect_count == 0

    def test_unknown_event_does_not_advance_funnel(self, journal_persisted_state):
        journal_persisted_state.onboarding_started_at = 1_000.0
        journal_state.save_persisted_state(journal_persisted_state)
        unknown_event_line = journal_models.JournalEventLine(
            event=journal_events.NodeJournalEvent.UNKNOWN,
            timestamp=1_010.0,
            session_id="session-1",
            install_id=journal_persisted_state.install_id,
            app_version=octobot_constants.LONG_VERSION,
            distribution="node",
            onboarding_complete=False,
            attributes=journal_models.JournalEventAttributes(raw_event_name="legacy_custom_event"),
        )
        summary = journey_summary_module.build_journey_summary([unknown_event_line])
        assert summary.furthest_step_reached is None
        assert summary.last_successful_step is None
        assert summary.step_durations_seconds == {}
        assert summary.first_failure is None


class TestBuildUploadEnvelope:
    def test_wraps_events_with_install_metadata(self, journal_persisted_state):
        journal_persisted_state.onboarding_started_at = 1_000.0
        journal_state.save_persisted_state(journal_persisted_state)
        events = _load_golden_events()

        envelope = journey_summary_module.build_upload_envelope(
            events,
            app_version=octobot_constants.LONG_VERSION,
            note="beta feedback",
        )

        assert envelope.install_id == journal_persisted_state.install_id
        assert envelope.app_version == octobot_constants.LONG_VERSION
        assert envelope.onboarding_started_at == 1_000.0
        assert envelope.onboarding_complete is True
        assert envelope.events == events
        assert envelope.event_count == len(events)
        assert envelope.uploaded is False
        assert envelope.ready is True
        assert envelope.note == "beta feedback"
        assert envelope.journey_summary.furthest_step_reached == (
            journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED.value
        )
