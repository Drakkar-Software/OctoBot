#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import datetime

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models

import octobot_sync.constants as sync_constants
import octobot_node.protocol.debug as debug_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


class TestGetDebugState:
    """Checks :func:`octobot_node.protocol.debug.get_debug_state`."""

    @pytest.mark.asyncio
    async def test_assembles_debug_state_from_dependencies(self):
        sample_automations = [
            protocol_models.AutomationState(
                id="auto-1",
                status=protocol_models.WorkflowStatus.RUNNING,
                metadata=protocol_models.AutomationMetadata(
                    name="auto",
                    description="auto description",
                    created_at=_SAMPLE_TIMESTAMP,
                    updated_at=_SAMPLE_TIMESTAMP,
                ),
                exchange_account_ids=["acc-bound"],
            ),
        ]
        sample_user_actions = [
            protocol_models.UserAction(id="ua-1"),
        ]
        sample_accounts = [
            protocol_models.Account(
                id="acc-a",
                name="Alpha",
                is_simulated=False,
                created_at=_SAMPLE_TIMESTAMP,
                updated_at=_SAMPLE_TIMESTAMP,
            ),
        ]
        sample_exchange_configs = [
            protocol_models.ExchangeConfig(
                id="cfg-a",
                name="binance-main",
                exchange="binance",
                sandboxed=False,
            ),
        ]
        sample_strategies = [
            protocol_models.Strategy(
                id="strat-a",
                version="1.0.0",
                name="Strategy A",
                reference_market="USDT",
                created_at=_SAMPLE_TIMESTAMP,
                updated_at=_SAMPLE_TIMESTAMP,
                configuration=protocol_models.StrategyConfiguration(
                    protocol_models.GenericProcessConfiguration(
                        configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                        profile_data={},
                    ),
                ),
            ),
        ]
        sample_trading_summaries = [
            protocol_models.AccountTradingWithAccountId(
                account_id="acc-bound",
                account_trading=protocol_models.AccountTrading(
                    updated_at=_SAMPLE_TIMESTAMP,
                ),
            ),
        ]
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=sample_accounts,
            exchange_configs=sample_exchange_configs,
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=sample_strategies,
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=sample_automations),
            ) as get_automation_states_mock,
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=sample_user_actions),
            ) as list_user_actions_mock,
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=sample_trading_summaries,
            ) as get_account_trading_summaries_mock,
        ):
            debug_state = await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        get_automation_states_mock.assert_awaited_once_with(_TEST_WALLET_ADDRESS)
        list_user_actions_mock.assert_awaited_once_with(_TEST_WALLET_ADDRESS, active_only=False)
        get_account_trading_summaries_mock.assert_called_once_with(
            _TEST_WALLET_ADDRESS,
            ["acc-bound"],
        )
        assert debug_state.version == sync_constants.DEBUG_STATE_VERSION
        assert debug_state.debug is not None
        assert debug_state.debug.automations == sample_automations
        assert debug_state.debug.user_actions == sample_user_actions
        assert debug_state.debug.accounts == sample_accounts
        assert debug_state.debug.exchange_configs == sample_exchange_configs
        assert debug_state.debug.local_strategies == sample_strategies
        assert debug_state.debug.account_tradings == sample_trading_summaries

    @pytest.mark.asyncio
    async def test_redacts_auth_details_in_automations(self):
        automation_with_auth = protocol_models.AutomationState(
            id="auto-auth",
            status=protocol_models.WorkflowStatus.COMPLETED,
            metadata=protocol_models.AutomationMetadata(
                name="auto",
                description="",
            ),
            actions=[
                protocol_models.Action(
                    id="action-1",
                    action_type="apply_configuration",
                    status=protocol_models.WorkflowStatus.COMPLETED,
                    configuration={
                        "exchange_account_details": {
                            "auth_details": {
                                "api_key": "secret-key",
                                "api_secret": "secret-secret",
                                "api_password": "secret-pass",
                            },
                        },
                    },
                ),
            ],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[automation_with_auth]),
            ),
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ),
        ):
            debug_state = await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        assert debug_state.debug is not None
        assert debug_state.debug.automations is not None
        auth_details = debug_state.debug.automations[0].actions[0].configuration[
            "exchange_account_details"
        ]["auth_details"]
        assert auth_details["api_key"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert auth_details["api_secret"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert auth_details["api_password"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_leaves_non_config_actions_unchanged(self):
        dsl_action = protocol_models.Action(
            id="dsl-1",
            action_type="dsl_script",
            status=protocol_models.WorkflowStatus.COMPLETED,
            dsl='run_octobot_process("acc", {}, [{"api_key": "leak"}])',
        )
        automation = protocol_models.AutomationState(
            id="auto-dsl",
            status=protocol_models.WorkflowStatus.COMPLETED,
            metadata=protocol_models.AutomationMetadata(name="auto", description=""),
            actions=[dsl_action],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[automation]),
            ),
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ),
        ):
            debug_state = await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        returned_action = debug_state.debug.automations[0].actions[0]
        assert returned_action is dsl_action
        assert returned_action.dsl == dsl_action.dsl

    @pytest.mark.asyncio
    async def test_leaves_apply_configuration_without_auth_unchanged(self):
        config_action = protocol_models.Action(
            id="action-1",
            action_type="apply_configuration",
            status=protocol_models.WorkflowStatus.COMPLETED,
            configuration={
                "exchange_account_details": {
                    "auth_details": {},
                },
            },
        )
        automation = protocol_models.AutomationState(
            id="auto-sim",
            status=protocol_models.WorkflowStatus.COMPLETED,
            metadata=protocol_models.AutomationMetadata(name="auto", description=""),
            actions=[config_action],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[automation]),
            ),
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ),
        ):
            debug_state = await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        returned_action = debug_state.debug.automations[0].actions[0]
        assert returned_action is config_action
        assert returned_action.configuration == config_action.configuration

    @pytest.mark.asyncio
    async def test_empty_collections_when_dependencies_return_empty(self):
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ) as get_account_trading_summaries_mock,
        ):
            debug_state = await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        get_account_trading_summaries_mock.assert_called_once_with(_TEST_WALLET_ADDRESS, [])
        assert debug_state.debug is not None
        assert debug_state.debug.automations == []
        assert debug_state.debug.user_actions == []
        assert debug_state.debug.accounts == []
        assert debug_state.debug.exchange_configs == []
        assert debug_state.debug.local_strategies == []
        assert debug_state.debug.account_tradings == []

    @pytest.mark.asyncio
    async def test_ignores_exchange_account_ids_when_automation_not_running(self):
        completed_automation = protocol_models.AutomationState(
            id="auto-completed",
            status=protocol_models.WorkflowStatus.COMPLETED,
            metadata=protocol_models.AutomationMetadata(name="auto", description=""),
            exchange_account_ids=["acc-ignored"],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )
        strategies_state = protocol_models.StrategiesState(
            version=sync_constants.USER_STRATEGIES_STATE_VERSION,
            strategies=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[completed_automation]),
            ),
            mock.patch.object(
                debug_module.scheduler_api,
                "list_user_actions",
                mock.AsyncMock(return_value=[]),
            ),
            mock.patch.object(
                debug_module.accounts_protocol,
                "get_accounts_state",
                return_value=accounts_state,
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=strategies_state,
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ) as get_account_trading_summaries_mock,
        ):
            await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        get_account_trading_summaries_mock.assert_called_once_with(_TEST_WALLET_ADDRESS, [])
