#  Drakkar-Software OctoBot-Flow

import contextlib
import datetime

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_flow.entities
import octobot_flow.jobs.global_view_account_job as global_view_account_job_module
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module
import octobot_flow.logic.global_view.exchange_account_refresh as exchange_account_refresh_module
import octobot_flow.logic.global_view.global_view_persistence as global_view_persistence_module
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module
import octobot_sync.constants as sync_constants
from tests.logic.global_view.portfolio_test_util import wire_portfolio_pipeline


def _open_order_dict(exchange_id: str, symbol: str = "BTC/USDT") -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0,
        }
    }


def _portfolio_content() -> dict:
    return {
        "USDT": {
            commons_constants.PORTFOLIO_TOTAL: 1000.0,
            commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
        },
        "BTC": {
            commons_constants.PORTFOLIO_TOTAL: 0.1,
            commons_constants.PORTFOLIO_AVAILABLE: 0.1,
        },
    }


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _empty_portfolio_history_state() -> protocol_models.PortfolioHistoricalValuesState:
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=None,
    )


def _exchange_account_context(
    *,
    has_bound_automation: bool = False,
    is_simulated: bool = True,
) -> octobot_flow.entities.GlobalViewAccountContext:
    account_id = "functional-account-1"
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=["exchange-config-1"],
    )
    account_assets = None
    if is_simulated:
        account_assets = [
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=[
                    protocol_models.DetailedAsset(
                        symbol="USDT",
                        total=1000.0,
                        available=1000.0,
                    ),
                ],
            ),
        ]
    account = protocol_models.Account(
        id=account_id,
        name="Functional account",
        is_simulated=is_simulated,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        assets=account_assets,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
    )
    exchange_config = protocol_models.ExchangeConfig(
        id="exchange-config-1",
        name="binance-main",
        exchange="binanceus",
        sandboxed=False,
    )
    auth_details = exchange_data_module.ExchangeAuthDetails(
        exchange_type=trading_enums.ExchangeTypes.SPOT.value,
        sandboxed=False,
        exchange_account_id=account_id,
    )
    return octobot_flow.entities.GlobalViewAccountContext(
        account=account,
        exchange_account=exchange_account,
        exchange_config=exchange_config,
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=auth_details,
        has_bound_automation=has_bound_automation,
    )


@pytest.mark.asyncio
class TestGlobalViewAccountJobFunctional:
    async def test_refresh_simulated_account(self):
        context = _exchange_account_context()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=_portfolio_content())
        exchange_manager.exchange.get_open_orders = mock.AsyncMock(return_value=[])
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        wire_portfolio_pipeline(exchange_manager, {})
        portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
        portfolio_manager.apply_forced_portfolio = mock.Mock(
            side_effect=lambda portfolio_content, update_available_funds_from_open_orders=False: (
                portfolio_manager.handle_balance_update(portfolio_content)
            ),
        )

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        ensure_ticker_channel_mock = mock.AsyncMock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                ensure_ticker_channel_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                mock.AsyncMock(return_value={}),
            ),
            mock.patch.object(
                exchange_account_refresh_module.tickers_repository_module.TickersRepository,
                "fetch_tickers",
                mock.AsyncMock(return_value={}),
            ),
            mock.patch.object(
                global_view_account_job_module.tentacles_manager_api,
                "get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_order_exchange_ids",
                return_value=set(),
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_orders",
                return_value=[],
            ),
            mock.patch.object(
                global_view_persistence_module,
                "persist_global_view_refresh_result",
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        portfolio_manager.apply_forced_portfolio.assert_called_once()
        assert refresh_result.updated_account.assets
        asset_symbols = {
            asset.symbol
            for assets_for_trading_type in refresh_result.updated_account.assets
            for asset in assets_for_trading_type.assets
        }
        assert "USDT" in asset_symbols
        assert refresh_result.changed_order_ids == set()

    async def test_refresh_real_account_detects_disappeared_orders(self):
        context = _exchange_account_context(has_bound_automation=True, is_simulated=False)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=_portfolio_content())
        exchange_manager.exchange.get_open_orders = mock.AsyncMock(
            return_value=[_open_order_dict("stays-order-2")],
        )
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=None)
        wire_portfolio_pipeline(exchange_manager, {})
        previous_open_orders = [
            _open_order_dict("gone-order-1", "BTC/USDT"),
            _open_order_dict("stays-order-2", "ETH/USDT"),
        ]

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        ensure_ticker_channel_mock = mock.AsyncMock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                ensure_ticker_channel_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                mock.AsyncMock(return_value={}),
            ),
            mock.patch.object(
                global_view_account_job_module.tentacles_manager_api,
                "get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_order_exchange_ids",
                return_value={"gone-order-1", "stays-order-2"},
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_orders",
                return_value=previous_open_orders,
            ),
            mock.patch.object(
                global_view_persistence_module,
                "persist_global_view_refresh_result",
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        called_symbols = {
            call.kwargs.get("symbol")
            for call in exchange_manager.exchange.get_open_orders.await_args_list
        }
        assert called_symbols == {"BTC/USDT", "ETH/USDT"}
        assert refresh_result.updated_account.assets
        assert refresh_result.changed_order_ids == {"gone-order-1"}
