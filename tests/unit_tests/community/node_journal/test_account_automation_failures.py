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

import datetime

import octobot_protocol.models as protocol_models

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording

from .test_external_action_events import _user_action_for_type


class TestRecordAccountValidated:
    def test_records_validation_attributes(self, journal_persisted_state):
        journal_recording.record_account_validated(
            is_simulated=True,
            exchange_name="binanceus",
            user_action_id="ua-validated",
            account_count=2,
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNT_VALIDATED.value
        assert events[0]["attributes"]["is_simulated"] is True
        assert events[0]["attributes"]["exchange_name"] == "binanceus"
        assert events[0]["attributes"]["user_action_id"] == "ua-validated"
        assert events[0]["attributes"]["account_count"] == 2


class TestRecordAccountValidationFailed:
    def test_records_failure_with_user_action_id(self, journal_persisted_state):
        journal_recording.record_account_validation_failed(
            is_simulated=False,
            exchange_name="kraken",
            error=RuntimeError("invalid keys"),
            user_action_id="ua-retry-1",
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED.value
        assert events[0]["attributes"]["user_action_id"] == "ua-retry-1"
        assert events[0]["attributes"]["error_category"] == "RuntimeError"


class TestAccountCreateFailureRetryPairing:
    def test_failed_and_retry_attempts_share_user_action_id(self, journal_persisted_state):
        user_action_id = "ua-account-retry"
        user_action = _user_action_for_type(
            protocol_models.UserActionType.ACCOUNT_CREATE,
            action_id=user_action_id,
        )
        journal_recording.record_external_action_failed(
            user_action,
            source="sync",
            error=RuntimeError("first rejection"),
        )
        journal_recording.record_external_action_received(user_action, source="sync")

        events = journal_module.read_events()
        user_action_ids = [
            event_line["attributes"].get("user_action_id")
            for event_line in events
            if "user_action_id" in event_line["attributes"]
        ]
        assert user_action_id in user_action_ids
        assert events[-1]["event"] == journal_events.NodeJournalEvent.ACCOUNT_CREATE_ATTEMPT.value
