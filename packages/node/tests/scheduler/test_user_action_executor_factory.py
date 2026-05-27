#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import datetime
import importlib

import pytest

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor as user_actions_executor_package

executor_factory_module = importlib.import_module(
    "octobot_node.scheduler.user_actions.user_actions_executor.user_action_executor_factory",
)


class Test_user_action_executor_factory:
    """Scenarios for :func:`executor_factory_module.user_action_executor_factory`."""

    @staticmethod
    def _exchange_account_payload() -> protocol_models.ExchangeAccount:
        return protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            remote_account_id="remote-1",
            exchange_config_ids=["test-exchange-config-id"],
        )

    @classmethod
    def _minimal_exchange_account(cls, *, account_identifier: str) -> protocol_models.Account:
        return protocol_models.Account(
            id=account_identifier,
            name="Test account",
            is_simulated=True,
            created_at=datetime.datetime(2026, 2, 2, 10, 0, 0, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 2, 3, 15, 30, 0, tzinfo=datetime.UTC),
            specifics=protocol_models.AccountSpecifics(
                actual_instance=cls._exchange_account_payload(),
            ),
        )

    @staticmethod
    def _configuration_wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
        return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())

    def _user_action(self, *, action_identifier: str, configuration_inner) -> protocol_models.UserAction:
        return protocol_models.UserAction(
            id=action_identifier,
            configuration=self._configuration_wrap(configuration_inner),
        )

    def test_returns_create_automation_executor_class(self):
        configuration_inner = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="create-automation",
                created_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
                strategy=protocol_models.StrategyReference(
                    id="factory-create-strategy",
                    version="1.0.0",
                ),
                accounts=[protocol_models.AccountReference(id="acc-auto")],
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-create-auto", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.CreateAutomationActionExecutor

    def test_returns_edit_automation_executor_class(self):
        configuration_inner = protocol_models.EditAutomationConfiguration(
            id="auto-1",
            action_type=protocol_models.UserActionType.AUTOMATION_EDIT,
            configuration=protocol_models.AutomationConfiguration(
                name="edit-automation",
                created_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
                strategy=protocol_models.StrategyReference(
                    id="factory-edit-strategy",
                    version="1.0.0",
                ),
                accounts=[protocol_models.AccountReference(id="acc-edit")],
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-edit-auto", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.EditAutomationActionExecutor

    def test_returns_stop_automation_executor_class(self):
        configuration_inner = protocol_models.StopAutomationConfiguration(
            id="auto-stop",
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        user_action_model = self._user_action(action_identifier="ua-stop", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.StopAutomationActionExecutor

    def test_returns_signal_automation_executor_class(self):
        configuration_inner = protocol_models.SignalAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_SIGNAL,
            automation_id="auto-signal",
            signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
        )
        user_action_model = self._user_action(action_identifier="ua-signal", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.SignalAutomationActionExecutor

    def test_returns_create_account_executor_class(self):
        configuration_inner = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=self._minimal_exchange_account(account_identifier="new-acc"),
        )
        user_action_model = self._user_action(action_identifier="ua-create-acc", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.CreateAccountActionExecutor

    def test_returns_edit_account_executor_class(self):
        configuration_inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="edit-acc",
            configuration=self._minimal_exchange_account(account_identifier="edit-acc"),
        )
        user_action_model = self._user_action(action_identifier="ua-edit-acc", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.EditAccountActionExecutor

    def test_returns_delete_account_executor_class(self):
        configuration_inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="del-1",
        )
        user_action_model = self._user_action(action_identifier="ua-delete", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.DeleteAccountActionExecutor

    def test_returns_refresh_accounts_executor_class(self):
        configuration_inner = protocol_models.RefreshAccountsConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
        )
        user_action_model = self._user_action(action_identifier="ua-refresh", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.RefreshAccountsActionExecutor

    def test_returns_create_exchange_config_executor_class(self):
        configuration_inner = protocol_models.CreateExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            configuration=protocol_models.ExchangeConfig(
                id="new-config",
                name="binance-main",
                exchange="binanceus",
                sandboxed=False,
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-create-config", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.CreateExchangeConfigActionExecutor

    def test_returns_edit_exchange_config_executor_class(self):
        configuration_inner = protocol_models.EditExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
            id="edit-config",
            configuration=protocol_models.ExchangeConfig(
                id="edit-config",
                name="binance-main",
                exchange="binanceus",
                sandboxed=False,
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-edit-config", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.EditExchangeConfigActionExecutor

    def test_returns_delete_exchange_config_executor_class(self):
        configuration_inner = protocol_models.DeleteExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_DELETE,
            id="del-config",
        )
        user_action_model = self._user_action(action_identifier="ua-delete-config", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.DeleteExchangeConfigActionExecutor

    def test_returns_create_strategy_executor_class(self):
        configuration_inner = protocol_models.CreateStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_CREATE,
            configuration=protocol_models.Strategy(
                id="new-strategy",
                version="1.0.0",
                name="Factory strategy",
                reference_market="USDT",
                created_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
                updated_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
                configuration=protocol_models.StrategyConfiguration(
                    protocol_models.GenericProcessConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                        profile_data={},
                    ),
                ),
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-create-strategy", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.CreateStrategyActionExecutor

    def test_returns_edit_strategy_executor_class(self):
        strategy_model = protocol_models.Strategy(
            id="edit-strategy",
            version="1.0.0",
            name="Factory strategy",
            reference_market="USDT",
            created_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 2, 1, 12, 0, 0, tzinfo=datetime.UTC),
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.GenericProcessConfiguration(
                    configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                    profile_data={},
                ),
            ),
        )
        configuration_inner = protocol_models.EditStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_EDIT,
            id="edit-strategy",
            configuration=strategy_model,
        )
        user_action_model = self._user_action(action_identifier="ua-edit-strategy", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.EditStrategyActionExecutor

    def test_returns_delete_strategy_executor_class(self):
        configuration_inner = protocol_models.DeleteStrategyConfiguration(
            action_type=protocol_models.UserActionType.STRATEGY_DELETE,
            id="del-strategy",
        )
        user_action_model = self._user_action(action_identifier="ua-delete-strategy", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.DeleteStrategyActionExecutor

    def test_returns_create_account_auth_executor_class(self):
        configuration_inner = protocol_models.CreateAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
            configuration=protocol_models.AccountAuthentication(
                id="new-auth",
                api_key="key",
                api_secret="secret",
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-create-auth", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.CreateAccountAuthActionExecutor

    def test_returns_edit_account_auth_executor_class(self):
        configuration_inner = protocol_models.EditAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_EDIT,
            id="edit-auth",
            configuration=protocol_models.AccountAuthentication(
                id="edit-auth",
                api_key="key",
                api_secret="secret",
            ),
        )
        user_action_model = self._user_action(action_identifier="ua-edit-auth", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.EditAccountAuthActionExecutor

    def test_returns_delete_account_auth_executor_class(self):
        configuration_inner = protocol_models.DeleteAccountAuthConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_AUTH_DELETE,
            id="del-auth",
        )
        user_action_model = self._user_action(action_identifier="ua-delete-auth", configuration_inner=configuration_inner)
        resolved_executor_cls = executor_factory_module.user_action_executor_factory(user_action_model)
        assert resolved_executor_cls is user_actions_executor_package.DeleteAccountAuthActionExecutor

    def test_raises_when_configuration_is_none(self):
        user_action_model = protocol_models.UserAction(id="ua-no-configuration", configuration=None)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="UserAction.configuration is required"):
            executor_factory_module.user_action_executor_factory(user_action_model)

    def test_raises_when_configuration_actual_instance_is_none(self):
        configuration_model = protocol_models.UserActionConfiguration.model_construct(actual_instance=None)
        user_action_model = protocol_models.UserAction(id="ua-nil-instance", configuration=configuration_model)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="actual_instance is required"):
            executor_factory_module.user_action_executor_factory(user_action_model)

    def test_raises_when_actual_instance_has_unknown_type(self):
        configuration_model = protocol_models.UserActionConfiguration.model_construct(actual_instance=object())
        user_action_model = protocol_models.UserAction(id="ua-unknown-inner", configuration=configuration_model)
        with pytest.raises(
            node_errors.UnsupportedUserActionConfigurationTypeError,
            match="Unknown user action configuration type",
        ):
            executor_factory_module.user_action_executor_factory(user_action_model)
