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
import octobot.community.node_journal.recording.user_actions as user_actions_module

_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)


def _wrap_configuration(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _minimal_account(account_id: str = "acc-1") -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=True,
        created_at=_SAMPLE_TIMESTAMP,
        updated_at=_SAMPLE_TIMESTAMP,
        assets=[],
    )


def _minimal_strategy(strategy_id: str = "strategy-1") -> protocol_models.Strategy:
    configuration = protocol_models.GenericProcessConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
        profile_data={"profile_details": {"id": strategy_id}},
    )
    return protocol_models.Strategy(
        id=strategy_id,
        version="1.0.0",
        name="Test strategy",
        reference_market="USDT",
        created_at=_SAMPLE_TIMESTAMP,
        updated_at=_SAMPLE_TIMESTAMP,
        configuration=protocol_models.StrategyConfiguration(configuration),
    )


def _user_action_for_type(
    action_type: protocol_models.UserActionType,
    action_id: str = "ua-test",
) -> protocol_models.UserAction:
    if action_type == protocol_models.UserActionType.STRATEGY_CREATE:
        inner = protocol_models.CreateStrategyConfiguration(
            action_type=action_type,
            configuration=_minimal_strategy(),
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_EDIT:
        account_model = _minimal_account()
        inner = protocol_models.EditAccountConfiguration(
            action_type=action_type,
            id=account_model.id,
            configuration=account_model,
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_CREATE:
        inner = protocol_models.CreateAccountConfiguration(
            action_type=action_type,
            configuration=_minimal_account(),
        )
    else:
        raise ValueError(f"Unsupported action type for test helper: {action_type}")
    return protocol_models.UserAction(id=action_id, configuration=_wrap_configuration(inner))


class TestActionEventMapCompleteness:
    def test_every_handled_action_type_has_map_entry(self):
        handled_action_types = set(user_actions_module.ACTION_EVENT_MAP.keys())
        assert handled_action_types == {
            protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            protocol_models.UserActionType.ACCOUNT_CREATE,
            protocol_models.UserActionType.ACCOUNT_EDIT,
            protocol_models.UserActionType.STRATEGY_CREATE,
            protocol_models.UserActionType.STRATEGY_EDIT,
            protocol_models.UserActionType.AUTOMATION_CREATE,
            protocol_models.UserActionType.AUTOMATION_EDIT,
        }

    def test_attempt_failure_pairs_are_symmetric(self):
        for action_type, (attempt_event, failure_event) in user_actions_module.ACTION_EVENT_MAP.items():
            assert attempt_event is not None
            assert attempt_event.value.endswith("_attempt")
            if action_type == protocol_models.UserActionType.ACCOUNT_CREATE:
                assert failure_event is None
                continue
            assert failure_event is not None
            assert failure_event.value.endswith("_failed")
            assert attempt_event.value.removesuffix("_attempt") == failure_event.value.removesuffix("_failed")


class TestRecordExternalActionReceived:
    def test_records_received_and_strategy_create_attempt(self, journal_persisted_state):
        user_action = _user_action_for_type(
            protocol_models.UserActionType.STRATEGY_CREATE,
            action_id="ua-create",
        )
        journal_recording.record_external_action_received(user_action, source="sync")

        events = journal_module.read_events()
        event_names = [event_line.event for event_line in events]
        assert event_names == [
            journal_events.NodeJournalEvent.EXTERNAL_ACTION_RECEIVED,
            journal_events.NodeJournalEvent.STRATEGY_CREATE_ATTEMPT,
        ]
        assert events[0].attributes.source == "sync"
        assert events[0].attributes.action_type == protocol_models.UserActionType.STRATEGY_CREATE.value
        assert events[0].attributes.user_action_id == "ua-create"


class TestRecordExternalActionFailed:
    def test_records_failed_and_strategy_create_failed(self, journal_persisted_state):
        user_action = _user_action_for_type(
            protocol_models.UserActionType.STRATEGY_CREATE,
            action_id="ua-fail",
        )
        journal_recording.record_external_action_failed(
            user_action,
            source="debug_api",
            error=RuntimeError("strategy invalid"),
        )

        events = journal_module.read_events()
        event_names = [event_line.event for event_line in events]
        assert event_names == [
            journal_events.NodeJournalEvent.EXTERNAL_ACTION_FAILED,
            journal_events.NodeJournalEvent.STRATEGY_CREATE_FAILED,
        ]
        assert events[0].attributes.error_category == "RuntimeError"
        assert events[1].attributes.user_action_id == "ua-fail"


class TestRecordExecutorFailure:
    def test_records_typed_failure_for_account_edit(self, journal_persisted_state):
        user_action = _user_action_for_type(
            protocol_models.UserActionType.ACCOUNT_EDIT,
            action_id="ua-edit",
        )
        journal_recording.record_executor_failure(
            user_action,
            error=ValueError("bad account"),
        )

        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNT_EDIT_FAILED
        assert event_line.attributes.error_category == "ValueError"

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


class TestRecordExternalActionAccountCreateFailure:
    def test_account_create_failure_maps_to_account_validation_failed(self, journal_persisted_state):
        user_action = _user_action_for_type(
            protocol_models.UserActionType.ACCOUNT_CREATE,
            action_id="ua-account",
        )
        journal_recording.record_external_action_failed(
            user_action,
            source="sync",
            error=RuntimeError("account rejected"),
        )

        events = journal_module.read_events()
        validation_failures = [
            event_line
            for event_line in events
            if event_line.event == journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED
        ]
        assert len(validation_failures) == 1
        assert validation_failures[0].attributes.user_action_id == "ua-account"


class TestRecordStrategyCreateSucceeded:
    def test_records_strategy_metadata(self, journal_persisted_state):
        journal_recording.record_strategy_create_succeeded(
            strategy_id="strategy-create-1",
            configuration_type="generic_process",
            user_action_id="ua-create-strategy",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED
        assert event_line.attributes.strategy_id == "strategy-create-1"
        assert event_line.attributes.configuration_type == "generic_process"
        assert event_line.attributes.user_action_id == "ua-create-strategy"


class TestRecordStrategyEditSucceeded:
    def test_records_strategy_metadata(self, journal_persisted_state):
        journal_recording.record_strategy_edit_succeeded(
            strategy_id="strategy-edit-1",
            configuration_type="market_making",
            user_action_id="ua-edit-strategy",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED
        assert event_line.attributes.strategy_id == "strategy-edit-1"
        assert event_line.attributes.configuration_type == "market_making"
        assert event_line.attributes.user_action_id == "ua-edit-strategy"
