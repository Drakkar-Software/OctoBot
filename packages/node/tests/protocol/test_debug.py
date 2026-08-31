#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import datetime

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_sync.constants as sync_constants
import octobot_node.protocol.debug as debug_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _sample_account(account_id: str, name: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name=name,
        is_simulated=False,
        created_at=_SAMPLE_TIMESTAMP,
        updated_at=_SAMPLE_TIMESTAMP,
    )


def _empty_accounts_state() -> protocol_models.AccountsState:
    return protocol_models.AccountsState(
        version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
        accounts=[],
        exchange_configs=[],
    )


def _empty_strategies_state() -> protocol_models.StrategiesState:
    return protocol_models.StrategiesState(
        version=sync_constants.USER_STRATEGIES_STATE_VERSION,
        strategies=[],
    )


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
            _sample_account("acc-a", "Alpha"),
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
                account_id="acc-a",
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
            ["acc-a"],
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
    async def test_empty_collections_when_dependencies_return_empty(self):
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
                return_value=_empty_accounts_state(),
            ),
            mock.patch.object(
                debug_module.strategies_protocol,
                "get_strategies_state",
                return_value=_empty_strategies_state(),
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
    async def test_loads_trading_summaries_for_all_wallet_accounts_even_without_running_automation(
        self,
    ):
        completed_automation = protocol_models.AutomationState(
            id="auto-completed",
            status=protocol_models.WorkflowStatus.COMPLETED,
            metadata=protocol_models.AutomationMetadata(name="auto", description=""),
            exchange_account_ids=["acc-ignored"],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[
                _sample_account("acc-a", "Alpha"),
                _sample_account("acc-b", "Beta"),
            ],
            exchange_configs=[],
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
                return_value=_empty_strategies_state(),
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ) as get_account_trading_summaries_mock,
        ):
            await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        get_account_trading_summaries_mock.assert_called_once_with(
            _TEST_WALLET_ADDRESS,
            ["acc-a", "acc-b"],
        )

    @pytest.mark.asyncio
    async def test_ignores_running_automation_binding_when_loading_trading_summaries(self):
        running_automation = protocol_models.AutomationState(
            id="auto-running",
            status=protocol_models.WorkflowStatus.RUNNING,
            metadata=protocol_models.AutomationMetadata(name="auto", description=""),
            exchange_account_ids=["acc-bound"],
        )
        accounts_state = protocol_models.AccountsState(
            version=sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
            accounts=[
                _sample_account("acc-a", "Alpha"),
                _sample_account("acc-b", "Beta"),
            ],
            exchange_configs=[],
        )
        with (
            mock.patch.object(
                debug_module.scheduler_api,
                "get_automation_states",
                mock.AsyncMock(return_value=[running_automation]),
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
                return_value=_empty_strategies_state(),
            ),
            mock.patch.object(
                debug_module.accounts_trading_protocol,
                "get_account_trading_summaries",
                return_value=[],
            ) as get_account_trading_summaries_mock,
        ):
            await debug_module.get_debug_state(_TEST_WALLET_ADDRESS)
        get_account_trading_summaries_mock.assert_called_once_with(
            _TEST_WALLET_ADDRESS,
            ["acc-a", "acc-b"],
        )


class TestWalletAccountIds:
    def test_returns_empty_list_when_accounts_is_none(self):
        assert debug_module._wallet_account_ids(None) == []

    def test_returns_all_non_empty_account_ids(self):
        accounts = [
            _sample_account("acc-a", "Alpha"),
            _sample_account("acc-b", "Beta"),
        ]
        assert debug_module._wallet_account_ids(accounts) == ["acc-a", "acc-b"]

    def test_skips_accounts_with_empty_id(self):
        accounts = [
            _sample_account("acc-a", "Alpha"),
            protocol_models.Account(
                id="",
                name="Missing id",
                is_simulated=False,
                created_at=_SAMPLE_TIMESTAMP,
                updated_at=_SAMPLE_TIMESTAMP,
            ),
        ]
        assert debug_module._wallet_account_ids(accounts) == ["acc-a"]
