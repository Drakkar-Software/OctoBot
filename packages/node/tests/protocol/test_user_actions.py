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

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.protocol.user_actions as user_actions_module
import octobot_node.user_actions.user_actions_executor as user_actions_executor_package
import octobot_node.scheduler as scheduler_module

_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def _exchange_account_payload() -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        exchange="binanceus",
        remote_account_id="remote-1",
        api_key="k",
        api_secret="s",
    )


def _minimal_exchange_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=True,
        details=protocol_models.AccountDetails(
            actual_instance=_exchange_account_payload(),
        ),
    )


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    # make sure json parse/dump works as expected
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


class Test_get_user_action_executor:
    def test_returns_create_automation_executor_class(self):
        inner = protocol_models.CreateAutomationConfiguration(
            action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
            configuration=protocol_models.AutomationConfiguration(
                name="create-automation",
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.IndexConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.INDEX,
                        coins=[protocol_models.IndexCoin(name="BTC", ratio=1.0)],
                        rebalance_trigger_min_percent=0.0,
                    )
                )
            )
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.CreateAutomationActionExecutor

    def test_returns_edit_automation_executor_class(self):
        inner = protocol_models.EditAutomationConfiguration(
            id="auto-1",
            action_type=protocol_models.UserActionType.AUTOMATION_EDIT,
            configuration=protocol_models.AutomationConfiguration(
                name="edit-automation",
                configuration=protocol_models.AutomationConfigurationConfiguration(
                    protocol_models.GridConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.GRID,
                        symbol="BTC/USDT",
                        spread=6,
                        increment=2,
                        buy_count=2,
                        sell_count=2,
                        enable_trailing_up=False,
                        enable_trailing_down=False,
                        order_by_order_trailing=False,
                    )
                ),
            ),
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.EditAutomationActionExecutor

    def test_returns_stop_automation_executor_class(self):
        inner = protocol_models.StopAutomationConfiguration(
            id="auto-stop",
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.StopAutomationActionExecutor

    def test_returns_create_account_executor_class(self):
        inner = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=_minimal_exchange_account(account_id="new-acc"),
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.CreateAccountActionExecutor

    def test_returns_edit_account_executor_class(self):
        account_model = _minimal_exchange_account(account_id="edit-acc")
        inner = protocol_models.EditAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_EDIT,
            id="edit-acc",
            configuration=account_model,
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.EditAccountActionExecutor

    def test_returns_delete_account_executor_class(self):
        inner = protocol_models.DeleteAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_DELETE,
            id="del-1",
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.DeleteAccountActionExecutor

    def test_returns_refresh_accounts_executor_class(self):
        inner = protocol_models.RefreshAccountsConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNTS_REFRESH,
        )
        executor_cls = user_actions_module._get_user_action_executor(_wrap(inner))
        assert executor_cls is user_actions_executor_package.RefreshAccountsActionExecutor

    def test_raises_when_actual_instance_is_none(self):
        configuration = protocol_models.UserActionConfiguration.model_construct(actual_instance=None)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="actual_instance is required"):
            user_actions_module._get_user_action_executor(configuration)

    def test_raises_when_actual_instance_has_unknown_type(self):
        configuration = protocol_models.UserActionConfiguration.model_construct(actual_instance=object())
        with pytest.raises(node_errors.UnsupportedUserActionConfigurationTypeError, match="Unknown user action configuration type"):
            user_actions_module._get_user_action_executor(configuration)


class Test_execute_user_action:
    @pytest.mark.asyncio
    async def test_raises_when_configuration_is_none(self):
        user_action = protocol_models.UserAction(id="ua-1", configuration=None)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="UserAction.configuration is required"):
            await user_actions_module.execute_user_action(user_action, _WALLET_ADDRESS)

    @pytest.mark.asyncio
    async def test_raises_when_configuration_actual_instance_is_none(self):
        configuration = protocol_models.UserActionConfiguration.model_construct(actual_instance=None)
        user_action = protocol_models.UserAction(id="ua-2", configuration=configuration)
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="actual_instance is required"):
            await user_actions_module.execute_user_action(user_action, _WALLET_ADDRESS)

    @pytest.mark.asyncio
    async def test_dispatches_stop_automation_executor_without_error(self):
        inner = protocol_models.StopAutomationConfiguration(
            id="auto-stop",
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        user_action = protocol_models.UserAction(id="ua-stop", configuration=_wrap(inner))
        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        with (
            mock.patch(
                "octobot_node.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=["workflow-for-auto-stop"],
            ),
        ):
            result = await user_actions_module.execute_user_action(user_action, _WALLET_ADDRESS)
        assert result is None
        mock_dbos_instance.send_async.assert_awaited_once()
