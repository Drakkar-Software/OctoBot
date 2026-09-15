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
import octobot_trading.personal_data as personal_data
import octobot_flow.logic.global_view.exchange_account_refresh as exchange_account_refresh_module
import octobot_flow.logic.global_view.global_view_persistence as global_view_persistence_module
import octobot_sync.constants as sync_constants
from tests.logic.global_view.portfolio_test_util import patch_temporary_exchange_channel_ensure
from tests.logic.global_view.portfolio_test_util import wire_portfolio_pipeline
from tests.logic.global_view.portfolio_test_util import wire_repository_factory


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


def _exchange_account_context(
    *,
    account_id: str = "account-1",
    is_simulated: bool = False,
    has_bound_automation: bool = False,
) -> octobot_flow.entities.GlobalViewAccountContext:
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=["exchange-config-1"],
    )
    account = protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=is_simulated,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
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


def _empty_portfolio_history_state() -> protocol_models.PortfolioHistoricalValuesState:
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=None,
    )


def _patch_repository_factory(exchange_manager, balance_content: dict, **kwargs):
    factory, portfolio_repository, orders_repository, tickers_repository = wire_repository_factory(
        exchange_manager,
        balance_content,
        **kwargs,
    )
    factory_patch = mock.patch.object(
        exchange_account_refresh_module,
        "_create_exchange_repository_factory",
        mock.Mock(return_value=factory),
    )
    return factory_patch, factory, portfolio_repository, orders_repository, tickers_repository


@pytest.mark.asyncio
class TestGlobalViewAccountJobRun:
    async def test_run_returns_refresh_result_shape(self):
        context = _exchange_account_context()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        wire_portfolio_pipeline(exchange_manager, {})
        factory_patch, _factory, portfolio_repository, orders_repository, _tickers_repository = (
            _patch_repository_factory(exchange_manager, _portfolio_content())
        )

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        persist_mock = mock.Mock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            patch_temporary_exchange_channel_ensure() as (
                ensure_ticker_channel_mock,
                ensure_balance_channel_mock,
                ensure_orders_channel_mock,
            ),
            mock.patch.object(
                personal_data,
                "refresh_portfolio_valuation",
                mock.Mock(),
            ),
            factory_patch,
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
                persist_mock,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_balance_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_orders_channel_mock.assert_not_awaited()
        portfolio_repository.fetch_and_apply_portfolio.assert_awaited_once()
        orders_repository.fetch_open_orders.assert_not_called()
        persist_mock.assert_called_once()
        assert persist_mock.call_args.kwargs["persist_open_orders"] is False
        assert isinstance(refresh_result, octobot_flow.entities.GlobalViewAccountRefreshResult)
        assert refresh_result.updated_account.id == "account-1"
        assert refresh_result.changed_order_ids == set()
        assert refresh_result.open_orders == []
        assert refresh_result.updated_account.assets is not None
        assert refresh_result.updated_account.assets[0].assets

    async def test_run_detects_disappeared_orders(self):
        context = _exchange_account_context(has_bound_automation=True)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=None)
        wire_portfolio_pipeline(exchange_manager, {})
        previous_open_orders = [
            _open_order_dict("gone-order-1", "BTC/USDT"),
            _open_order_dict("stays-order-2", "ETH/USDT"),
        ]
        factory_patch, _factory, _portfolio_repository, orders_repository, _tickers_repository = (
            _patch_repository_factory(
                exchange_manager,
                _portfolio_content(),
                open_orders=[_open_order_dict("stays-order-2")],
            )
        )

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        persist_mock = mock.Mock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            patch_temporary_exchange_channel_ensure() as (
                ensure_ticker_channel_mock,
                ensure_balance_channel_mock,
                ensure_orders_channel_mock,
            ),
            mock.patch.object(
                personal_data,
                "refresh_portfolio_valuation",
                mock.Mock(),
            ),
            factory_patch,
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
                persist_mock,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        orders_repository.fetch_open_orders.assert_awaited_once_with(["BTC/USDT", "ETH/USDT"])
        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_balance_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_orders_channel_mock.assert_awaited_once_with(exchange_manager)
        assert persist_mock.call_args.kwargs["persist_open_orders"] is False
        assert refresh_result.changed_order_ids == {"gone-order-1"}

    async def test_unbound_fetches_open_orders_by_previous_symbols(self):
        context = _exchange_account_context()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=None)
        wire_portfolio_pipeline(exchange_manager, {})
        previous_open_orders = [
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "gone-order-1",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                }
            },
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "stays-order-2",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
                }
            },
        ]
        factory_patch, _factory, _portfolio_repository, orders_repository, _tickers_repository = (
            _patch_repository_factory(
                exchange_manager,
                _portfolio_content(),
                open_orders=[_open_order_dict("stays-order-2")],
            )
        )

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        persist_mock = mock.Mock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            patch_temporary_exchange_channel_ensure() as (
                ensure_ticker_channel_mock,
                ensure_balance_channel_mock,
                ensure_orders_channel_mock,
            ),
            mock.patch.object(
                personal_data,
                "refresh_portfolio_valuation",
                mock.Mock(),
            ),
            factory_patch,
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
                persist_mock,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        orders_repository.fetch_open_orders.assert_awaited_once_with(["BTC/USDT", "ETH/USDT"])
        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_balance_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_orders_channel_mock.assert_awaited_once_with(exchange_manager)
        assert persist_mock.call_args.kwargs["persist_open_orders"] is True
        assert refresh_result.changed_order_ids == {"gone-order-1"}

    async def test_simulated_account_uses_fill_detector_without_exchange_fetch(self):
        context = _exchange_account_context(account_id="sim-account", is_simulated=True)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        wire_portfolio_pipeline(exchange_manager, {}, portfolio_total=0.0)
        previous_open_orders = [
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "filled-order",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 10000.0,
                    trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: False,
                }
            },
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "open-order",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 8000.0,
                    trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: False,
                }
            },
        ]
        create_factory_mock = mock.Mock()

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        persist_mock = mock.Mock()
        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
            ),
            patch_temporary_exchange_channel_ensure() as (
                ensure_ticker_channel_mock,
                ensure_balance_channel_mock,
                ensure_orders_channel_mock,
            ),
            mock.patch.object(
                personal_data,
                "refresh_portfolio_valuation",
                mock.Mock(),
            ),
            mock.patch.object(
                global_view_account_job_module.tentacles_manager_api,
                "get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch.object(
                global_view_account_job_module.simulated_portfolio_seeder_module,
                "seed_simulated_portfolio",
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_order_exchange_ids",
                return_value={"filled-order", "open-order"},
            ),
            mock.patch.object(
                account_state_persistence_module,
                "load_previous_open_orders",
                return_value=previous_open_orders,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                mock.AsyncMock(return_value={
                    "BTC/USDT": {
                        trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 9000.0,
                    },
                }),
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_create_exchange_repository_factory",
                create_factory_mock,
            ),
            mock.patch.object(
                global_view_persistence_module,
                "persist_global_view_refresh_result",
                persist_mock,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        ensure_ticker_channel_mock.assert_awaited_once_with(exchange_manager)
        ensure_balance_channel_mock.assert_not_awaited()
        ensure_orders_channel_mock.assert_not_awaited()
        create_factory_mock.assert_not_called()
        assert persist_mock.call_args.kwargs["persist_open_orders"] is True
        assert refresh_result.changed_order_ids == {"filled-order"}
        remaining_exchange_ids = personal_data.open_order_exchange_ids_from_open_orders(
            refresh_result.open_orders
        )
        assert remaining_exchange_ids == {"open-order"}

    async def test_generic_account_returns_no_op_result(self):
        generic_account = protocol_models.Account(
            id="generic-1",
            name="Generic",
            is_simulated=False,
            created_at=_TEST_TIMESTAMP,
            updated_at=_TEST_TIMESTAMP,
            specifics=protocol_models.AccountSpecifics(
                actual_instance=protocol_models.GenericAccount(
                    account_type=protocol_models.AccountType.GENERIC,
                ),
            ),
        )
        context = octobot_flow.entities.GlobalViewAccountContext(
            account=generic_account,
            exchange_account=protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                remote_account_id="unused",
                exchange_config_ids=["exchange-config-1"],
            ),
            exchange_config=protocol_models.ExchangeConfig(
                id="exchange-config-1",
                name="binance-main",
                exchange="binanceus",
                sandboxed=False,
            ),
            trading_type=protocol_models.TradingType.SPOT,
            auth_details=exchange_data_module.ExchangeAuthDetails(
                exchange_type=trading_enums.ExchangeTypes.SPOT.value,
                sandboxed=False,
            ),
        )
        refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
            "wallet-1",
            context,
        ).run()
        assert refresh_result.updated_account.id == "generic-1"
        assert refresh_result.changed_order_ids == set()
