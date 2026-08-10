#  Drakkar-Software OctoBot-Flow

import contextlib
import datetime

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_flow.entities
import octobot_flow.jobs.global_view_account_job as global_view_account_job_module
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module
import octobot_flow.logic.global_view.global_view_persistence as global_view_persistence_module
import octobot_sync.constants as sync_constants


def _open_order_dict(exchange_id: str) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,
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


def _exchange_account_context() -> octobot_flow.entities.GlobalViewAccountContext:
    account_id = "functional-account-1"
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=["exchange-config-1"],
    )
    account = protocol_models.Account(
        id=account_id,
        name="Functional account",
        is_simulated=True,
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
    )


@pytest.mark.asyncio
class TestGlobalViewAccountJobFunctional:
    async def test_refresh_simulated_account(self):
        context = _exchange_account_context()
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=_portfolio_content())
        exchange_manager.exchange.get_open_orders = mock.AsyncMock(return_value=[])
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data.portfolio_manager = None

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
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
                global_view_persistence_module,
                "persist_global_view_refresh_result",
            ),
            mock.patch.object(
                account_state_persistence_module,
                "build_portfolio_history_state",
                side_effect=lambda user_id, account_id, snapshot, valuation_unit, evaluation_time: (
                    protocol_models.PortfolioHistoricalValuesState(
                        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
                        history=protocol_models.PortfolioHistoricalValues(
                            unit=valuation_unit,
                            values=[snapshot],
                        ),
                    )
                ),
            ),
            mock.patch.object(
                trading_api,
                "get_portfolio",
                return_value=_portfolio_content(),
            ),
            mock.patch.object(
                trading_api,
                "get_current_portfolio_value",
                return_value=1500.0,
            ),
            mock.patch.object(
                trading_api,
                "get_current_crypto_currency_value",
                side_effect=lambda _exchange_manager, symbol: 50000.0 if symbol == "BTC" else 1.0,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        assert refresh_result.portfolio_history_state is not None
        assert refresh_result.portfolio_history_state.history is not None
        assert refresh_result.portfolio_history_state.history.unit == "USDC"
        assert refresh_result.portfolio_history_state.history.values[-1].total == 1500.0
        assert refresh_result.updated_account.assets
        assert refresh_result.changed_order_ids == set()

    async def test_refresh_real_account_detects_disappeared_orders(self):
        context = _exchange_account_context()
        context.account.is_simulated = False
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=_portfolio_content())
        exchange_manager.exchange.get_open_orders = mock.AsyncMock(
            return_value=[_open_order_dict("stays-order-2")],
        )
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=None)
        exchange_manager.exchange_personal_data.portfolio_manager = None

        @contextlib.asynccontextmanager
        async def fake_exchange_manager(*_args, **_kwargs):
            yield exchange_manager

        with (
            mock.patch.object(
                global_view_account_job_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager,
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
                global_view_persistence_module,
                "persist_global_view_refresh_result",
            ),
            mock.patch.object(
                account_state_persistence_module,
                "build_portfolio_history_state",
                side_effect=lambda user_id, account_id, snapshot, valuation_unit, evaluation_time: (
                    protocol_models.PortfolioHistoricalValuesState(
                        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
                        history=protocol_models.PortfolioHistoricalValues(
                            unit=valuation_unit,
                            values=[snapshot],
                        ),
                    )
                ),
            ),
            mock.patch.object(
                trading_api,
                "get_portfolio",
                return_value=_portfolio_content(),
            ),
            mock.patch.object(
                trading_api,
                "get_current_portfolio_value",
                return_value=1500.0,
            ),
            mock.patch.object(
                trading_api,
                "get_current_crypto_currency_value",
                side_effect=lambda _exchange_manager, symbol: 50000.0 if symbol == "BTC" else 1.0,
            ),
        ):
            refresh_result = await global_view_account_job_module.GlobalViewAccountJob(
                "wallet-1",
                context,
            ).run()

        assert refresh_result.portfolio_history_state is not None
        assert refresh_result.portfolio_history_state.history.unit == commons_constants.DEFAULT_REFERENCE_MARKET
        assert refresh_result.updated_account.assets
        assert refresh_result.changed_order_ids == {"gone-order-1"}
