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


def _account_auth_create_user_action(action_id: str = "ua-auth-create") -> protocol_models.UserAction:
    authentication_model = protocol_models.AccountAuthentication(
        id="auth-1",
        api_key="key",
        api_secret="secret",
        updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    inner = protocol_models.CreateAccountAuthConfiguration(
        action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
        configuration=authentication_model,
    )
    configuration_model = protocol_models.UserActionConfiguration.from_json(inner.to_json())
    return protocol_models.UserAction(id=action_id, configuration=configuration_model)


class TestRecordAccountAuthCreateSucceeded:
    def test_records_exchange_name_and_user_action_id(self, journal_persisted_state):
        journal_recording.record_account_auth_create_succeeded(
            exchange_name="binanceus",
            user_action_id="ua-auth-create",
        )
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED
        assert event_line.attributes.exchange_name == "binanceus"
        assert event_line.attributes.user_action_id == "ua-auth-create"


class TestRecordExternalActionReceivedAccountAuthCreate:
    def test_records_attempt_for_account_auth_create(self, journal_persisted_state):
        user_action = _account_auth_create_user_action()
        journal_recording.record_external_action_received(user_action, source="sync")

        events = journal_module.read_events()
        event_names = [event_line.event for event_line in events]
        assert journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_ATTEMPT in event_names
        attempt_event = next(
            event_line
            for event_line in events
            if event_line.event == journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_ATTEMPT
        )
        assert attempt_event.attributes.user_action_id == user_action.id
