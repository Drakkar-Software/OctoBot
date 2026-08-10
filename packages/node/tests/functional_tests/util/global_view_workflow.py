#  Drakkar-Software OctoBot-Node
"""Shared helpers for global view workflow functional tests."""

from __future__ import annotations

import contextlib
import datetime
import typing

import mock
import pytest

import octobot.community.authentication as community_authentication_module
import octobot_commons.constants as commons_constants
import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
import octobot_protocol.models as protocol_models
import octobot_sync.server as sync_server_module
import octobot_sync.sync.collection_providers as collection_providers_module
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector_module
import octobot_trading.exchanges.types.rest_exchange as rest_exchange_module

import octobot_node.scheduler.workflows_retention as workflows_retention_module

from tests.functional_tests.util import authenticator_mocks as authenticator_mocks_module
from tests.functional_tests.test_accounts_CRUD_operations import (
    _FUNCTIONAL_BTC_HOLDINGS,
    _FUNCTIONAL_ETH_HOLDINGS,
    _FUNCTIONAL_SOL_HOLDINGS,
    _FUNCTIONAL_USDT_HOLDINGS,
    _stub_get_balance_no_network,
    _stub_load_symbol_markets_no_network,
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


async def _stub_get_open_orders_no_network(self, symbol=None, since=None, limit=None, **kwargs):
    return []


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


def _protocol_order(exchange_id: str) -> protocol_models.Order:
    return protocol_models.Order(
        id=exchange_id,
        symbol="BTC/USDT",
        price=10000.0,
        quantity=0.01,
        filled=0.0,
        exchange_id=exchange_id,
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        status=protocol_models.OrderStatus.OPEN,
        created_at=_FUNCTIONAL_TIMESTAMP,
    )


def _open_order_storage_dict(exchange_id: str) -> dict:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            order_columns.EXCHANGE_ID.value: exchange_id,
            order_columns.ID.value: exchange_id,
            order_columns.SYMBOL.value: "BTC/USDT",
            order_columns.PRICE.value: 10000.0,
            order_columns.AMOUNT.value: 0.01,
            order_columns.FILLED.value: 0,
            order_columns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            order_columns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            order_columns.TRIGGER_ABOVE.value: False,
            order_columns.REDUCE_ONLY.value: False,
            order_columns.IS_ACTIVE.value: True,
            order_columns.STATUS.value: trading_enums.OrderStatus.OPEN.value,
            order_columns.TIMESTAMP.value: _FUNCTIONAL_TIMESTAMP.timestamp(),
        }
    }


def seed_account_trading_state(
    trading_provider: collection_providers_module.AccountTradingProvider,
    user_id: str,
    *,
    account_id: str,
    order_exchange_ids: list[str],
) -> None:
    trading_provider.save_state(
        user_id,
        account_id,
        protocol_models.AccountTradingState(
            version=collection_providers_module.AccountTradingProvider.STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_FUNCTIONAL_TIMESTAMP,
                orders=[_protocol_order(order_id) for order_id in order_exchange_ids],
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
    sim_open_order_ids: dict[str, list[str]] | None = None,
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

    configured_sim_open_order_ids = sim_open_order_ids or {}

    import octobot_flow.jobs.global_view_account_job as global_view_account_job_module
    import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module
    import octobot_trading.exchanges as trading_exchanges_module

    real_exchange_manager_from_exchange_data = trading_exchanges_module.exchange_manager_from_exchange_data

    @contextlib.asynccontextmanager
    async def exchange_manager_with_simulated_open_orders(
        exchange_data,
        profile_data,
        tentacles_setup_config,
        price_fallback=None,
    ):
        async with real_exchange_manager_from_exchange_data(
            exchange_data,
            profile_data,
            tentacles_setup_config,
            price_fallback=price_fallback,
        ) as exchange_manager:
            exchange_account_id = profile_data.exchanges[0].exchange_account_id
            open_order_ids_after_refresh = configured_sim_open_order_ids.get(exchange_account_id, [])

            async def patched_get_open_orders(**open_orders_kwargs):
                return [
                    _open_order_storage_dict(order_id)
                    for order_id in open_order_ids_after_refresh
                ]

            exchange_manager.exchange.get_open_orders = patched_get_open_orders

            real_get_balance = exchange_manager.exchange.get_balance

            async def patched_get_balance(**balance_kwargs):
                balance = await real_get_balance(**balance_kwargs)
                portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
                if portfolio_manager is not None and balance is not None:
                    portfolio_manager.handle_balance_update(balance)
                return balance

            exchange_manager.exchange.get_balance = patched_get_balance

            portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
            if portfolio_manager is not None:
                portfolio_manager.handle_mark_price_update = mock.AsyncMock(return_value=None)
            yield exchange_manager

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
            _stub_load_symbol_markets_no_network,
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
            trading_exchanges_module,
            "exchange_manager_from_exchange_data",
            exchange_manager_with_simulated_open_orders,
        ),
    ):
        account_provider.create_exchange_config(user_id, build_exchange_config())
        authentication_provider.create_item(user_id, build_functional_authentication())
        account_provider.create_item(user_id, build_real_account())
        account_provider.create_item(user_id, build_simulated_account(account_id=ACCOUNT_SIM_1_ID, account_name="Sim 1"))
        account_provider.create_item(user_id, build_simulated_account(account_id=ACCOUNT_SIM_2_ID, account_name="Sim 2"))
        for account_id, order_ids in configured_sim_open_order_ids.items():
            seed_account_trading_state(
                trading_provider,
                user_id,
                account_id=account_id,
                order_exchange_ids=order_ids,
            )
        try:
            yield {
                "user_id": user_id,
                "account_provider": account_provider,
                "trading_provider": trading_provider,
                "history_provider": history_provider,
            }
        finally:
            user_root_provider.set_root(previous_user_root)


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
