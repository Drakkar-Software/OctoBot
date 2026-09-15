#  Drakkar-Software OctoBot-Node

import datetime
import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module
import octobot_node.scheduler.automations.trade_symbols_resolver as trade_symbols_resolver_module
from tests.scheduler.user_actions.user_actions_executor.util import trading_tentacles_test_utils
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading


_TEST_WALLET_ID = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
_TEST_ACCOUNT_ID = "1f2e203f-bdfa-49a6-8427-71c19fdc3327"
_TEST_EXCHANGE_CONFIG_ID = "kraken-spot-config"
_TEST_TIMESTAMP = datetime.datetime(2026, 1, 10, 12, 0, 0, tzinfo=datetime.UTC)


def _kraken_exchange_config(
    *,
    historical_trade_symbols: list[str] | None = None,
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=_TEST_EXCHANGE_CONFIG_ID,
        name="kraken-main",
        exchange="kraken",
        sandboxed=False,
        historical_trade_symbols=historical_trade_symbols,
    )


def _kraken_account(
    account_id: str = _TEST_ACCOUNT_ID,
) -> protocol_models.Account:
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=[_TEST_EXCHANGE_CONFIG_ID],
    )
    return protocol_models.Account(
        id=account_id,
        name="Kraken real spot",
        is_simulated=False,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
    )


def _automation_state(
    automation_id: str,
    *,
    account_id: str,
    status: protocol_models.WorkflowStatus = protocol_models.WorkflowStatus.RUNNING,
    order_symbols: list[str] | None = None,
) -> protocol_models.AutomationState:
    return protocol_models.AutomationState(
        id=automation_id,
        status=status,
        metadata=protocol_models.AutomationMetadata(
            name=automation_id,
            description=automation_id,
        ),
        exchange_account_ids=[account_id],
        orders=[
            protocol_models.OrderSummary(id=f"order-{symbol_index}", symbol=symbol)
            for symbol_index, symbol in enumerate(order_symbols or [])
        ],
    )


def _wallet_automation_states(
    *,
    protocol_states: list[protocol_models.AutomationState] | None = None,
    flow_states_by_id: dict | None = None,
) -> automation_states_loader_module.WalletAutomationStates:
    return automation_states_loader_module.WalletAutomationStates(
        protocol_states=protocol_states or [],
        flow_states_by_id=flow_states_by_id or {},
    )


class TestResolveTradeSymbolsFromConfig:
    @pytest.mark.asyncio
    async def test_returns_historical_trade_symbols_from_realistic_exchange_config(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(
            historical_trade_symbols=["SOL/USDC"],
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(return_value=_wallet_automation_states()),
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == ["SOL/USDC"]


class TestResolveTradeSymbolsFromAutomations:
    @pytest.mark.asyncio
    async def test_unions_config_symbols_with_running_automation_order_symbols(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(
            historical_trade_symbols=["SOL/USDC"],
        )
        automation = _automation_state(
            "automation-dca",
            account_id=_TEST_ACCOUNT_ID,
            order_symbols=["BTC/USDC"],
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(
                return_value=_wallet_automation_states(protocol_states=[automation]),
            ),
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == ["BTC/USDC", "SOL/USDC"]

    @pytest.mark.asyncio
    async def test_includes_strategy_traded_symbols_from_running_automation(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(historical_trade_symbols=[])
        automation = _automation_state(
            "automation-dca",
            account_id=_TEST_ACCOUNT_ID,
        )
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config=trading_tentacles_test_utils.dca_tentacle_config(
            **{dca_trading.DCATradingMode.TRADING_PAIRS: ["BTC/USDC"]},
        ),
        )
        stored_strategy = protocol_models.Strategy(
            id="strategy-dca-1",
            version="1.0.0",
            name="DCA strategy",
            reference_market="USDC",
            created_at=_TEST_TIMESTAMP,
            updated_at=_TEST_TIMESTAMP,
            configuration=protocol_models.StrategyConfiguration(
                actual_instance=trading_configuration,
            ),
        )
        flow_automation_state = mock.Mock()
        flow_automation_state.automation.metadata.strategy_id = "strategy-dca-1"
        strategy_provider_mock = mock.Mock()
        strategy_provider_mock.get_item.return_value = stored_strategy
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(
                return_value=_wallet_automation_states(
                    protocol_states=[automation],
                    flow_states_by_id={"automation-dca": flow_automation_state},
                ),
            ),
        ), mock.patch.object(
            trade_symbols_resolver_module.collection_providers.StrategyProvider,
            "instance",
            return_value=strategy_provider_mock,
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == ["BTC/USDC"]
        strategy_provider_mock.get_item.assert_called_once_with(
            _TEST_WALLET_ID,
            "strategy-dca-1",
        )

    @pytest.mark.asyncio
    async def test_ignores_stopped_automations(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(historical_trade_symbols=[])
        automation = _automation_state(
            "automation-stopped",
            account_id=_TEST_ACCOUNT_ID,
            status=protocol_models.WorkflowStatus.COMPLETED,
            order_symbols=["BTC/USDC"],
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(
                return_value=_wallet_automation_states(protocol_states=[automation]),
            ),
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == []

    @pytest.mark.asyncio
    async def test_ignores_automations_bound_to_other_accounts(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(historical_trade_symbols=[])
        automation = _automation_state(
            "automation-foreign",
            account_id="other-account-id",
            order_symbols=["BTC/USDC"],
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(
                return_value=_wallet_automation_states(protocol_states=[automation]),
            ),
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == []


class TestResolveTradeSymbolsWithPreloadedAutomationStates:
    @pytest.mark.asyncio
    async def test_uses_preloaded_automation_states_without_scheduler_fetches(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(historical_trade_symbols=["SOL/USDC"])
        automation = _automation_state(
            "automation-dca",
            account_id=_TEST_ACCOUNT_ID,
            order_symbols=["BTC/USDC"],
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=mock.AsyncMock(),
        ) as load_wallet_automation_states_mock:
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
                automation_states=[automation],
                flow_automation_states_by_id={},
            )
        assert resolved_symbols == ["BTC/USDC", "SOL/USDC"]
        load_wallet_automation_states_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_loads_wallet_automation_states_once_when_both_inputs_missing(self):
        account = _kraken_account()
        exchange_config = _kraken_exchange_config(historical_trade_symbols=["SOL/USDC"])
        automation = _automation_state(
            "automation-dca",
            account_id=_TEST_ACCOUNT_ID,
            order_symbols=["BTC/USDC"],
        )
        load_wallet_automation_states_mock = mock.AsyncMock(
            return_value=_wallet_automation_states(protocol_states=[automation]),
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_wallet_automation_states",
            new=load_wallet_automation_states_mock,
        ):
            resolved_symbols = await trade_symbols_resolver_module.resolve_trade_symbols(
                _TEST_WALLET_ID,
                account,
                exchange_config,
            )
        assert resolved_symbols == ["BTC/USDC", "SOL/USDC"]
        load_wallet_automation_states_mock.assert_awaited_once_with(_TEST_WALLET_ID)
