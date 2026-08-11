#  Drakkar-Software OctoBot-Node
"""Shared helpers for global view workflow functional tests."""

from __future__ import annotations

import contextlib
import datetime
import decimal
import typing

import mock
import pytest

import octobot.community.authentication as community_authentication_module
import octobot_commons.constants as commons_constants
import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
import octobot_protocol.models as protocol_models
import octobot_sync.server as sync_server_module
import octobot_sync.sync.collection_providers as collection_providers_module
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector_module
import octobot_trading.exchanges.types.rest_exchange as rest_exchange_module
import octobot_trading.enums as trading_enums

import octobot_node.scheduler.workflows_retention as workflows_retention_module

from tests.functional_tests.util import authenticator_mocks as authenticator_mocks_module
from tests.functional_tests.test_accounts_CRUD_operations import (
    _FUNCTIONAL_BTC_HOLDINGS,
    _FUNCTIONAL_ETH_HOLDINGS,
    _FUNCTIONAL_SOL_HOLDINGS,
    _FUNCTIONAL_USDT_HOLDINGS,
    _stub_get_balance_no_network,
)

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_WALLET_PASSPHRASE = "globalViewPW1!"
_FUNCTIONAL_TIMESTAMP = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)
_EXCHANGE_CONFIG_ID = "global-view-functional-exchange-config"

ACCOUNT_REAL_ID = "acc-real"
ACCOUNT_SIM_1_ID = "acc-sim-1"
ACCOUNT_SIM_2_ID = "acc-sim-2"

AUTOMATION_FILL_ID = "automation-gv-fill"
AUTOMATION_NO_TRIGGER_ID = "automation-gv-no-trigger"
ORDER_FILL_ID = "gv-order-fill-1"
ORDER_STAYS_OPEN_ID = "gv-order-stays-open"

WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0

_FUNCTIONAL_VALUATION_TICKER_CLOSE_BY_SYMBOL = {
    "BTC/USDT": 50000.0,
    "ETH/USDT": 3000.0,
    "SOL/USDT": 100.0,
}


async def _stub_get_open_orders_no_network(self, symbol=None, since=None, limit=None, **kwargs):
    return []


async def _stub_load_symbol_markets_for_global_view(self, reload=False, market_filter=None):
    self.client.markets = {
        "BTC/USDT": {"symbol": "BTC/USDT", "active": True, "spot": True, "id": "BTCUSDT"},
        "ETH/USDT": {"symbol": "ETH/USDT", "active": True, "spot": True, "id": "ETHUSDT"},
        "SOL/USDT": {"symbol": "SOL/USDT", "active": True, "spot": True, "id": "SOLUSDT"},
        "SOL/BTC": {"symbol": "SOL/BTC", "active": True, "spot": True, "id": "SOLBTC"},
    }
    self.client.symbols = list(self.client.markets.keys())


def derive_user_id() -> str:
    return sync_server_module.derive_user_id(_TEST_PRIVATE_KEY)


def build_exchange_config() -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=_EXCHANGE_CONFIG_ID,
        name="binance-main",
        exchange="binanceus",
        sandboxed=False,
    )


def build_exchange_account(*, remote_account_id: str) -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=remote_account_id,
        exchange_config_ids=[_EXCHANGE_CONFIG_ID],
    )


def build_simulated_account(
    *,
    account_id: str,
    account_name: str,
    usdt_total: float = 1000.0,
) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=_FUNCTIONAL_TIMESTAMP,
        updated_at=_FUNCTIONAL_TIMESTAMP,
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=[
                    protocol_models.DetailedAsset(
                        symbol="USDT",
                        total=usdt_total,
                        available=usdt_total,
                    )
                ],
            )
        ],
        specifics=protocol_models.AccountSpecifics(
            actual_instance=build_exchange_account(remote_account_id=account_id),
        ),
    )


def build_real_account() -> protocol_models.Account:
    return protocol_models.Account(
        id=ACCOUNT_REAL_ID,
        name="Global view real account",
        is_simulated=False,
        created_at=_FUNCTIONAL_TIMESTAMP,
        updated_at=_FUNCTIONAL_TIMESTAMP,
        authentication_id="global-view-functional-auth",
        specifics=protocol_models.AccountSpecifics(
            actual_instance=build_exchange_account(remote_account_id=ACCOUNT_REAL_ID),
        ),
    )


def build_functional_authentication() -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id="global-view-functional-auth",
        api_key="functional-test-api-key",
        api_secret="functional-test-api-secret",
    )


def _protocol_order(
    exchange_id: str,
    *,
    price: float = 10000.0,
    trigger_above: bool = False,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=exchange_id,
        symbol="BTC/USDT",
        price=price,
        quantity=0.01,
        filled=0.0,
        exchange_id=exchange_id,
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        status=protocol_models.OrderStatus.OPEN,
        created_at=_FUNCTIONAL_TIMESTAMP,
        trigger_above=trigger_above,
    )


def seed_account_trading_state(
    trading_provider: collection_providers_module.AccountTradingProvider,
    user_id: str,
    *,
    account_id: str,
    seeded_orders: list[dict[str, typing.Any]],
) -> None:
    protocol_orders = [
        _protocol_order(
            seeded_order["exchange_id"],
            price=float(seeded_order.get("price", 10000.0)),
            trigger_above=bool(seeded_order.get("trigger_above", False)),
        )
        for seeded_order in seeded_orders
    ]
    trading_provider.save_state(
        user_id,
        account_id,
        protocol_models.AccountTradingState(
            version=collection_providers_module.AccountTradingProvider.STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_FUNCTIONAL_TIMESTAMP,
                orders=protocol_orders,
                trades=[],
                positions=[],
            ),
        ),
    )


def build_running_automation_state(
    automation_id: str,
    *,
    account_id: str,
    order_ids: list[str],
) -> protocol_models.AutomationState:
    return protocol_models.AutomationState(
        id=automation_id,
        status=protocol_models.WorkflowStatus.RUNNING,
        metadata=protocol_models.AutomationMetadata(
            name=automation_id,
            description=automation_id,
        ),
        exchange_account_ids=[account_id],
        orders=[
            protocol_models.OrderSummary(id=order_id, symbol="BTC/USDT")
            for order_id in order_ids
        ],
    )


async def enqueue_and_await_global_view_refresh() -> dict[str, typing.Any]:
    import octobot_node.scheduler
    import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module

    scheduled_time = datetime.datetime.now(datetime.UTC)
    workflow_handle = await octobot_node.scheduler.SCHEDULER.GLOBAL_VIEW_QUEUE.enqueue_async(
        global_view_workflow_module.GlobalViewRefreshWorkflow.global_view_refresh,
        scheduled_time,
        None,
    )
    return await workflow_handle.get_result()


@contextlib.asynccontextmanager
async def global_view_functional_environment(
    tmp_path,
    *,
    sim_ticker_close_by_symbol: dict[str, float] | None = None,
):
    user_root_provider = user_root_folder_provider_module.instance()
    previous_user_root = user_root_provider.get_root()
    test_user_root = tmp_path / "global_view_functional_user_root"
    user_root_provider.set_root(str(test_user_root))

    authentication_instance = authenticator_mocks_module.build_community_authentication(
        _TEST_PRIVATE_KEY,
        _TEST_WALLET_PASSPHRASE,
    )
    user_id = derive_user_id()

    account_provider = collection_providers_module.AccountProvider(base_folder=str(test_user_root))
    authentication_provider = collection_providers_module.AccountAuthenticationProvider(
        base_folder=str(test_user_root),
    )
    trading_provider = collection_providers_module.AccountTradingProvider(base_folder=str(test_user_root))
    history_provider = collection_providers_module.AccountHistoryProvider(base_folder=str(test_user_root))

    configured_sim_ticker_close_by_symbol = sim_ticker_close_by_symbol or {}

    import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module
    import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module

    async def patched_fetch_ticker_close_by_symbol(_exchange_manager, symbols):
        return {
            symbol: configured_sim_ticker_close_by_symbol[symbol]
            for symbol in symbols
            if symbol in configured_sim_ticker_close_by_symbol
        }

    async def patched_fetch_tickers(_self, symbols):
        if not symbols:
            return {}
        close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
        ticker_close_by_symbol = {
            **_FUNCTIONAL_VALUATION_TICKER_CLOSE_BY_SYMBOL,
            **configured_sim_ticker_close_by_symbol,
        }
        return {
            symbol: {close_column: decimal.Decimal(str(ticker_close_by_symbol[symbol]))}
            for symbol in symbols
            if symbol in ticker_close_by_symbol
        }

    with (
        mock.patch.object(
            community_authentication_module.CommunityAuthentication,
            "instance",
            return_value=authentication_instance,
        ),
        mock.patch.object(
            collection_providers_module.AccountProvider,
            "instance",
            return_value=account_provider,
        ),
        mock.patch.object(
            collection_providers_module.AccountAuthenticationProvider,
            "instance",
            return_value=authentication_provider,
        ),
        mock.patch.object(
            collection_providers_module.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ),
        mock.patch.object(
            collection_providers_module.AccountHistoryProvider,
            "instance",
            return_value=history_provider,
        ),
        mock.patch.object(
            workflows_retention_module,
            "should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ),
        mock.patch.object(
            account_state_updater_module,
            "_fetch_api_key_rights",
            mock.AsyncMock(return_value=[]),
        ),
        mock.patch.object(
            ccxt_connector_module.CCXTConnector,
            "load_symbol_markets",
            _stub_load_symbol_markets_for_global_view,
        ),
        mock.patch.object(
            ccxt_connector_module.CCXTConnector,
            "get_balance",
            _stub_get_balance_no_network,
        ),
        mock.patch.object(
            ccxt_connector_module.CCXTConnector,
            "get_open_orders",
            _stub_get_open_orders_no_network,
        ),
        mock.patch.object(
            tickers_repository_module.TickersRepository,
            "fetch_ticker_close_by_symbol",
            patched_fetch_ticker_close_by_symbol,
        ),
        mock.patch.object(
            tickers_repository_module.TickersRepository,
            "fetch_tickers",
            patched_fetch_tickers,
        ),
    ):
        account_provider.create_exchange_config(user_id, build_exchange_config())
        authentication_provider.create_item(user_id, build_functional_authentication())
        account_provider.create_item(user_id, build_real_account())
        account_provider.create_item(user_id, build_simulated_account(account_id=ACCOUNT_SIM_1_ID, account_name="Sim 1"))
        account_provider.create_item(user_id, build_simulated_account(account_id=ACCOUNT_SIM_2_ID, account_name="Sim 2"))
        try:
            yield {
                "user_id": user_id,
                "account_provider": account_provider,
                "trading_provider": trading_provider,
                "history_provider": history_provider,
            }
        finally:
            user_root_provider.set_root(previous_user_root)


def assert_simulated_account_assets(
    account: protocol_models.Account,
    *,
    expected_total: float,
) -> None:
    assert account.assets is not None
    flattened_assets: list[protocol_models.DetailedAsset] = []
    for assets_for_trading_type in account.assets:
        flattened_assets.extend(assets_for_trading_type.assets or [])
    assets_by_symbol = {asset.symbol: asset for asset in flattened_assets}
    assert "USDT" in assets_by_symbol
    assert assets_by_symbol["USDT"].total == pytest.approx(expected_total)


def assert_real_account_assets(account: protocol_models.Account) -> None:
    assert account.assets is not None
    flattened_assets: list[protocol_models.DetailedAsset] = []
    for assets_for_trading_type in account.assets:
        flattened_assets.extend(assets_for_trading_type.assets or [])
    assets_by_symbol = {asset.symbol: asset for asset in flattened_assets}
    assert set(assets_by_symbol) == {"USDT", "BTC", "ETH", "SOL"}
    assert assets_by_symbol["USDT"].total == pytest.approx(_FUNCTIONAL_USDT_HOLDINGS)
    assert assets_by_symbol["BTC"].total == pytest.approx(_FUNCTIONAL_BTC_HOLDINGS)
    assert assets_by_symbol["ETH"].total == pytest.approx(_FUNCTIONAL_ETH_HOLDINGS)
    assert assets_by_symbol["SOL"].total == pytest.approx(_FUNCTIONAL_SOL_HOLDINGS)
