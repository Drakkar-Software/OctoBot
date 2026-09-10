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


def _wrap_configuration(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


class TestRecordExecutorFailure:
    def test_maps_account_auth_create_to_account_auth_create_failed(self, journal_persisted_state):
        authentication_model = protocol_models.AccountAuthentication(
            id="auth-fail",
            api_key="key",
            api_secret="secret",
            updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        )
        inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=authentication_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-auth-fail",
            configuration=_wrap_configuration(inner),
        )
        journal_recording.record_executor_failure(
            user_action,
            error=RuntimeError("auth create failed"),
        )
        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_FAILED
        assert event_line.attributes.user_action_id == user_action.id

    def test_maps_strategy_edit_to_strategy_edit_failed(self, journal_persisted_state):
        strategy_configuration = protocol_models.GenericProcessConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
            profile_data={"profile_details": {"id": "strategy-edit"}},
        )
        strategy_model = protocol_models.Strategy(
            id="strategy-edit",
            version="1.0.0",
            name="Edited",
            reference_market="USDT",
            created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            configuration=protocol_models.StrategyConfiguration(strategy_configuration),
        )
        inner = protocol_models.EditStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="strategy-edit",
            configuration=strategy_model,
        )
        user_action = protocol_models.UserAction(
            id="ua-strategy-edit-fail",
            configuration=_wrap_configuration(inner),
        )
        journal_recording.record_executor_failure(
            user_action,
            error=ValueError("invalid profile"),
        )
        events = journal_module.read_events()
        assert events[0].event == journal_events.NodeJournalEvent.STRATEGY_EDIT_FAILED
