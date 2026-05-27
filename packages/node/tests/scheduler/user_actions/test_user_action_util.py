#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime

import pytest
import octobot_protocol.models as protocol_models

import octobot_node.scheduler.user_actions.user_action_util as user_action_util


_UPDATED_AT = datetime.datetime(2026, 3, 1, 10, 0, 0, tzinfo=datetime.UTC)
_ERROR_DETAILS = "workflow failed"
_AUTOMATION_CONFIGURATION = protocol_models.AutomationConfiguration(
    name="test-automation",
    created_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
    strategy=protocol_models.StrategyReference(
        id="strategy-1",
        version="1.0.0",
    ),
    accounts=[protocol_models.AccountReference(id="acc-1")],
)
_EXCHANGE_CONFIG = protocol_models.ExchangeConfig(
    id="cfg-1",
    name="binance-main",
    exchange="binanceus",
    sandboxed=False,
)


def _wrap_configuration(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _user_action_with_configuration(configuration_inner) -> protocol_models.UserAction:
    return protocol_models.UserAction(
        id="ua-test",
        configuration=_wrap_configuration(configuration_inner),
    )


class TestResolveUserActionResultType:
    def test_defaults_to_account_when_configuration_missing(self):
        user_action = protocol_models.UserAction(id="ua-no-config", configuration=None)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.ACCOUNT
        )

    def test_account_action_returns_account(self):
        configuration_inner = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=protocol_models.Account(
                id="acc-1",
                name="Test account",
                is_simulated=True,
                created_at=_UPDATED_AT,
                updated_at=_UPDATED_AT,
                specifics=protocol_models.AccountSpecifics(
                    actual_instance=protocol_models.ExchangeAccount(
                        account_type=protocol_models.AccountType.EXCHANGE,
                        remote_account_id="remote-1",
                        exchange_config_ids=["cfg-1"],
                    ),
                ),
            ),
        )
        user_action = _user_action_with_configuration(configuration_inner)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.ACCOUNT
        )

    @pytest.mark.parametrize(
        "action_type",
        [
            protocol_models.UserActionType.AUTOMATION_CREATE,
            protocol_models.UserActionType.AUTOMATION_EDIT,
            protocol_models.UserActionType.AUTOMATION_STOP,
            protocol_models.UserActionType.AUTOMATION_SIGNAL,
        ],
    )
    def test_automation_actions_return_automation(self, action_type):
        if action_type == protocol_models.UserActionType.AUTOMATION_STOP:
            configuration_inner = protocol_models.StopAutomationConfiguration(
                id="auto-stop",
                action_type=action_type,
            )
        elif action_type == protocol_models.UserActionType.AUTOMATION_SIGNAL:
            configuration_inner = protocol_models.SignalAutomationConfiguration(
                action_type=action_type,
                automation_id="auto-signal",
                signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
            )
        elif action_type == protocol_models.UserActionType.AUTOMATION_EDIT:
            configuration_inner = protocol_models.EditAutomationConfiguration(
                id="auto-1",
                action_type=action_type,
                configuration=_AUTOMATION_CONFIGURATION,
            )
        else:
            configuration_inner = protocol_models.CreateAutomationConfiguration(
                action_type=action_type,
                configuration=_AUTOMATION_CONFIGURATION,
            )
        user_action = _user_action_with_configuration(configuration_inner)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.AUTOMATION
        )

    @pytest.mark.parametrize(
        "action_type",
        [
            protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE,
        ],
    )
    def test_exchange_config_actions_return_exchange_config(self, action_type):
        if action_type == protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE:
            configuration_inner = protocol_models.DeleteExchangeConfigConfiguration(
                action_type=action_type,
                id="cfg-1",
            )
        elif action_type == protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT:
            configuration_inner = protocol_models.EditExchangeConfigConfiguration(
                action_type=action_type,
                id="cfg-1",
                configuration=_EXCHANGE_CONFIG,
            )
        else:
            configuration_inner = protocol_models.CreateExchangeConfigConfiguration(
                action_type=action_type,
                configuration=_EXCHANGE_CONFIG,
            )
        user_action = _user_action_with_configuration(configuration_inner)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.EXCHANGE_CONFIG
        )

    @pytest.mark.parametrize(
        "action_type",
        [
            protocol_models.UserActionType.STRATEGY_CREATE,
            protocol_models.UserActionType.STRATEGY_EDIT,
            protocol_models.UserActionType.STRATEGY_DELETE,
        ],
    )
    def test_strategy_actions_return_strategy(self, action_type):
        strategy_model = protocol_models.Strategy(
            id="strat-1",
            version="1.0.0",
            name="Test strategy",
            reference_market="USDT",
            created_at=_UPDATED_AT,
            updated_at=_UPDATED_AT,
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.GenericProcessConfiguration(
                    configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                    profile_data={},
                ),
            ),
        )
        if action_type == protocol_models.UserActionType.STRATEGY_DELETE:
            configuration_inner = protocol_models.DeleteStrategyConfiguration(
                action_type=action_type,
                id="strat-1",
            )
        elif action_type == protocol_models.UserActionType.STRATEGY_EDIT:
            configuration_inner = protocol_models.EditStrategyConfiguration(
                action_type=action_type,
                id="strat-1",
                configuration=strategy_model,
            )
        else:
            configuration_inner = protocol_models.CreateStrategyConfiguration(
                action_type=action_type,
                configuration=strategy_model,
            )
        user_action = _user_action_with_configuration(configuration_inner)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.STRATEGY
        )

    @pytest.mark.parametrize(
        "action_type",
        [
            protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            protocol_models.UserActionType.ACCOUNT_AUTH_EDIT,
            protocol_models.UserActionType.ACCOUNT_AUTH_DELETE,
        ],
    )
    def test_account_auth_actions_return_account_auth(self, action_type):
        authentication_model = protocol_models.AccountAuthentication(
            id="auth-1",
            api_key="key",
            api_secret="secret",
        )
        if action_type == protocol_models.UserActionType.ACCOUNT_AUTH_DELETE:
            configuration_inner = protocol_models.DeleteAccountAuthConfiguration(
                action_type=action_type,
                id="auth-1",
            )
        elif action_type == protocol_models.UserActionType.ACCOUNT_AUTH_EDIT:
            configuration_inner = protocol_models.EditAccountAuthConfiguration(
                action_type=action_type,
                id="auth-1",
                configuration=authentication_model,
            )
        else:
            configuration_inner = protocol_models.CreateAccountAuthConfiguration(
                action_type=action_type,
                configuration=authentication_model,
            )
        user_action = _user_action_with_configuration(configuration_inner)
        assert (
            user_action_util.resolve_user_action_result_type(user_action)
            == protocol_models.UserActionResultType.ACCOUNT_AUTH
        )


class TestBuildSynthesizedFailureUserActionResult:
    def test_automation_result(self):
        result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=protocol_models.UserActionResultType.AUTOMATION,
            updated_at=_UPDATED_AT,
            error_details=_ERROR_DETAILS,
        )
        inner = result.actual_instance
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.AUTOMATION
        assert inner.updated_at == _UPDATED_AT
        assert inner.error_message == protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details == _ERROR_DETAILS

    def test_exchange_config_result(self):
        result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=protocol_models.UserActionResultType.EXCHANGE_CONFIG,
            updated_at=_UPDATED_AT,
            error_details=_ERROR_DETAILS,
        )
        inner = result.actual_instance
        assert isinstance(inner, protocol_models.ExchangeConfigActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.EXCHANGE_CONFIG
        assert inner.updated_at == _UPDATED_AT
        assert inner.error_message == protocol_models.ExchangeConfigActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details == _ERROR_DETAILS

    def test_strategy_result(self):
        result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=protocol_models.UserActionResultType.STRATEGY,
            updated_at=_UPDATED_AT,
            error_details=_ERROR_DETAILS,
        )
        inner = result.actual_instance
        assert isinstance(inner, protocol_models.StrategyActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.STRATEGY
        assert inner.updated_at == _UPDATED_AT
        assert inner.error_message == protocol_models.StrategyActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details == _ERROR_DETAILS

    def test_account_auth_result(self):
        result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=protocol_models.UserActionResultType.ACCOUNT_AUTH,
            updated_at=_UPDATED_AT,
            error_details=_ERROR_DETAILS,
        )
        inner = result.actual_instance
        assert isinstance(inner, protocol_models.AccountAuthActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.ACCOUNT_AUTH
        assert inner.updated_at == _UPDATED_AT
        assert inner.error_message == protocol_models.AccountAuthActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details == _ERROR_DETAILS

    def test_account_result_for_account_type(self):
        result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=protocol_models.UserActionResultType.ACCOUNT,
            updated_at=_UPDATED_AT,
            error_details=_ERROR_DETAILS,
        )
        inner = result.actual_instance
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.ACCOUNT
        assert inner.updated_at == _UPDATED_AT
        assert inner.error_message == protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details == _ERROR_DETAILS


class TestBuildMinimalUserActionForWorkflow:
    def test_pending_when_not_terminal(self):
        user_action = user_action_util.build_minimal_user_action_for_workflow(
            workflow_id="wf-1",
            terminal=False,
            updated_at=_UPDATED_AT,
            parse_error="could not parse inputs",
            partial_user_action_id="ua-partial",
        )
        assert user_action.id == "ua-partial"
        assert user_action.status == protocol_models.UserActionStatus.PENDING
        assert user_action.result is None

    def test_failed_when_terminal(self):
        user_action = user_action_util.build_minimal_user_action_for_workflow(
            workflow_id="wf-2",
            terminal=True,
            updated_at=_UPDATED_AT,
            parse_error="could not parse inputs",
            workflow_error="dbos boom",
        )
        assert user_action.id == "wf-2"
        assert user_action.status == protocol_models.UserActionStatus.FAILED
        inner = user_action.result.actual_instance
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert "dbos boom" in inner.error_details
