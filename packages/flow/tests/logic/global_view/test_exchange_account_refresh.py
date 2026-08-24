#  Drakkar-Software OctoBot-Flow

import contextlib
import datetime
import decimal

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors

import octobot_flow.logic.exchange.simulator.simulated_portfolio_seeder as simulated_portfolio_seeder_module
import octobot_flow.logic.global_view.exchange_account_refresh as exchange_account_refresh_module
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module
from tests.logic.global_view.portfolio_test_util import wire_portfolio_pipeline


def _open_order_dict(exchange_id: str, symbol: str) -> dict:
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


def _wire_portfolio_pipeline(exchange_manager, portfolio_content: dict, **kwargs) -> None:
    wire_portfolio_pipeline(exchange_manager, portfolio_content, **kwargs)


class TestFetchOpenOrdersForSymbols:
    @pytest.mark.asyncio
    async def test_bad_symbol_skips_that_symbol_and_keeps_others(self):
        eth_order = _open_order_dict("stays-order-2", "ETH/USDT")

        async def get_open_orders(*, symbol=None, **_kwargs):
            if symbol == "STRK/USDC":
                raise trading_errors.UnSupportedSymbolError(
                    "ob_kraken does not have market symbol STRK/USDC"
                )
            if symbol == "ETH/USDT":
                return [eth_order]
            raise AssertionError(f"Unexpected symbol: {symbol}")

        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_open_orders = mock.AsyncMock(side_effect=get_open_orders)

        open_orders = await exchange_account_refresh_module._fetch_open_orders_for_symbols(
            exchange_manager,
            ["STRK/USDC", "ETH/USDT"],
        )

        assert open_orders == [eth_order]


class TestRefreshExchangeAccountPortfolio:
    @pytest.mark.asyncio
    async def test_real_refresh_applies_balance_to_portfolio_manager(self):
        balance_content = _portfolio_content()
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=balance_content)
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data = mock.Mock()
        _wire_portfolio_pipeline(exchange_manager, {})
        ensure_ticker_channel_mock = mock.AsyncMock()
        refresh_valuation_mock = mock.AsyncMock()
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                ensure_ticker_channel_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                refresh_valuation_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                mock.AsyncMock(return_value={}),
            ),
        ):
            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                fetch_open_orders=False,
            )

        exchange_manager.exchange_personal_data.handle_portfolio_update.assert_awaited_once()
        applied_balance = exchange_manager.exchange_personal_data.handle_portfolio_update.await_args.args[0]
        assert applied_balance["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("0.1")
        assert applied_balance["USDT"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("1000.0")
        asset_symbols = {
            asset.symbol
            for assets_for_trading_type in refresh_result.assets
            for asset in assets_for_trading_type.assets
        }
        assert asset_symbols == {"USDT", "BTC"}

    @pytest.mark.asyncio
    async def test_real_refresh_without_handle_portfolio_update_would_fail(self):
        balance_content = _portfolio_content()
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=balance_content)
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data = mock.Mock()
        _wire_portfolio_pipeline(exchange_manager, {}, portfolio_total=0.0)
        exchange_manager.exchange_personal_data.handle_portfolio_update = mock.AsyncMock(return_value=False)
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                mock.AsyncMock(),
            ),
        ):
            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                fetch_open_orders=False,
            )

        assert refresh_result.assets == []
        assert refresh_result.ticker_closes == {}

    @pytest.mark.asyncio
    async def test_simulated_refresh_uses_seeded_account_assets(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data = mock.Mock()
        _wire_portfolio_pipeline(
            exchange_manager,
            {
                "USDC": {
                    commons_constants.PORTFOLIO_TOTAL: 1000.0,
                    commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
                },
            },
            portfolio_total=1000.0,
        )
        portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
        portfolio_manager.apply_forced_portfolio = mock.Mock(
            side_effect=lambda portfolio_content, update_available_funds_from_open_orders=False: (
                portfolio_manager.handle_balance_update(portfolio_content)
            ),
        )
        account = protocol_models.Account(
            id="sim-account-1",
            name="Simulated",
            is_simulated=True,
            created_at=datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC),
            assets=[
                protocol_models.DetailedAssetsForTradingType(
                    trading_type=protocol_models.TradingType.SPOT,
                    assets=[
                        protocol_models.DetailedAsset(
                            symbol="USDC",
                            total=1000.0,
                            available=1000.0,
                        ),
                    ],
                ),
            ],
            specifics=protocol_models.AccountSpecifics(
                actual_instance=protocol_models.ExchangeAccount(
                    account_type=protocol_models.AccountType.EXCHANGE,
                    remote_account_id="sim-account-1",
                    exchange_config_ids=["exchange-config-1"],
                ),
            ),
        )
        simulated_portfolio_seeder_module.seed_simulated_portfolio(exchange_manager, account)
        fetch_tickers_mock = mock.AsyncMock(return_value={})
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                fetch_tickers_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                mock.AsyncMock(),
            ),
        ):
            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                is_simulated=True,
                previous_open_orders=[],
            )

        fetch_tickers_mock.assert_awaited_once_with(exchange_manager, [])

        portfolio_manager.apply_forced_portfolio.assert_called_once()
        asset_symbols = {
            asset.symbol
            for assets_for_trading_type in refresh_result.assets
            for asset in assets_for_trading_type.assets
        }
        assert "USDC" in asset_symbols

    @pytest.mark.asyncio
    async def test_real_refresh_portfolio_total_positive_with_ticker_prices(self):
        balance_content = _portfolio_content()
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=balance_content)
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data = mock.Mock()
        _wire_portfolio_pipeline(exchange_manager, balance_content, portfolio_total=6000.0)
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                mock.AsyncMock(),
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
        ):
            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                fetch_open_orders=False,
            )

        assert isinstance(refresh_result.ticker_closes, dict)


class TestValuationSymbolsFromPortfolio:
    def test_skips_zero_holdings_and_valuation_unit(self):
        exchange_manager = mock.Mock()
        exchange_manager.client_symbols = ["BTC/USDC"]
        portfolio_content = {
            "USDC": {
                commons_constants.PORTFOLIO_TOTAL: 1000.0,
                commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
            },
            "BTC": {
                commons_constants.PORTFOLIO_TOTAL: 0.1,
                commons_constants.PORTFOLIO_AVAILABLE: 0.1,
            },
            "ETH": {
                commons_constants.PORTFOLIO_TOTAL: 0.0,
                commons_constants.PORTFOLIO_AVAILABLE: 0.0,
            },
        }
        valuation_symbols = exchange_account_refresh_module._valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            "USDC",
        )
        assert valuation_symbols == ["BTC/USDC"]

    def test_uses_bridge_symbols_when_direct_valuation_pair_missing(self):
        exchange_manager = mock.Mock()
        exchange_manager.client_symbols = ["APT/USD", "USDT/USD"]
        portfolio_content = {
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: 1000.0,
                commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
            },
            "APT": {
                commons_constants.PORTFOLIO_TOTAL: 10.0,
                commons_constants.PORTFOLIO_AVAILABLE: 10.0,
            },
        }
        valuation_symbols = exchange_account_refresh_module._valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            "USDT",
        )
        assert set(valuation_symbols) == {"APT/USD", "USDT/USD"}

    def test_does_not_use_usd_like_bridge_when_valuation_unit_is_not_usd_like(self):
        exchange_manager = mock.Mock()
        exchange_manager.client_symbols = ["APT/USD", "BTC/EUR"]
        portfolio_content = {
            "EUR": {
                commons_constants.PORTFOLIO_TOTAL: 1000.0,
                commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
            },
            "APT": {
                commons_constants.PORTFOLIO_TOTAL: 10.0,
                commons_constants.PORTFOLIO_AVAILABLE: 10.0,
            },
            "BTC": {
                commons_constants.PORTFOLIO_TOTAL: 0.1,
                commons_constants.PORTFOLIO_AVAILABLE: 0.1,
            },
        }
        valuation_symbols = exchange_account_refresh_module._valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            "EUR",
        )
        assert valuation_symbols == ["BTC/EUR"]


class TestRefreshPortfolioValuation:
    @pytest.mark.asyncio
    async def test_syncs_portfolio_value_without_profitability_update(self):
        exchange_manager = mock.Mock()
        portfolio_manager = mock.Mock()
        portfolio_value_holder = mock.Mock()
        portfolio_manager.portfolio_value_holder = portfolio_value_holder
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        exchange_manager.symbol_exists = mock.Mock(return_value=False)
        with (
            mock.patch.object(
                trading_api,
                "get_portfolio",
                return_value={
                    "USDT": {
                        commons_constants.PORTFOLIO_TOTAL: 1000.0,
                        commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
                    },
                },
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_valuation_symbols_from_portfolio",
                return_value=[],
            ),
        ):
            await exchange_account_refresh_module._refresh_portfolio_valuation(
                exchange_manager,
                "USDT",
            )

        portfolio_value_holder._sync_portfolio_current_value_using_available_currencies_values.assert_called_once_with(
            init_price_fetchers=False,
        )
        exchange_manager.exchange_personal_data.handle_portfolio_profitability_update.assert_not_called()
        portfolio_manager.handle_mark_price_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_applies_ticker_prices_via_update_last_price_not_handle_mark_price_update(self):
        exchange_manager = mock.Mock()
        portfolio_manager = mock.Mock()
        portfolio_value_holder = mock.Mock()
        value_converter = mock.Mock()
        portfolio_value_holder.value_converter = value_converter
        portfolio_manager.portfolio_value_holder = portfolio_value_holder
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        exchange_manager.symbol_exists = mock.Mock(return_value=False)
        tickers = {
            "BTC/USDT": {
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 50000,
            },
        }
        with (
            mock.patch.object(
                trading_api,
                "get_portfolio",
                return_value={
                    "USDT": {
                        commons_constants.PORTFOLIO_TOTAL: 1000.0,
                        commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
                    },
                    "BTC": {
                        commons_constants.PORTFOLIO_TOTAL: 0.1,
                        commons_constants.PORTFOLIO_AVAILABLE: 0.1,
                    },
                },
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_valuation_symbols_from_portfolio",
                return_value=["BTC/USDT"],
            ),
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "fetch_tickers",
                mock.AsyncMock(return_value=tickers),
            ),
        ):
            await exchange_account_refresh_module._refresh_portfolio_valuation(
                exchange_manager,
                "USDT",
            )

        value_converter.update_last_price.assert_called_once_with(
            "BTC/USDT",
            decimal.Decimal("50000"),
        )
        portfolio_manager.handle_mark_price_update.assert_not_called()
        portfolio_value_holder._sync_portfolio_current_value_using_available_currencies_values.assert_called_once_with(
            init_price_fetchers=False,
        )


class TestRefreshExchangeAccountLogging:
    @pytest.mark.asyncio
    async def test_logs_fetched_portfolio_once_at_info(self):
        balance_content = _portfolio_content()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.exchange.get_balance = mock.AsyncMock(return_value=balance_content)
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")
        exchange_manager.exchange_personal_data = mock.Mock()
        _wire_portfolio_pipeline(exchange_manager, balance_content, portfolio_total=6000.0)
        logger_mock = mock.Mock()
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                mock.AsyncMock(),
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
                exchange_account_refresh_module,
                "_get_logger",
                return_value=logger_mock,
            ),
        ):
            await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                fetch_open_orders=False,
            )

        portfolio_log_calls = [
            call_args
            for call_args in logger_mock.info.call_args_list
            if call_args.args and call_args.args[0] == "Fetched [%s] full [%s] portfolio: %s"
        ]
        assert len(portfolio_log_calls) == 1
        assert portfolio_log_calls[0].args[1] == "binance"
        assert portfolio_log_calls[0].args[2] == "real"


class TestSimulatedTickerFetchMerge:
    @pytest.mark.asyncio
    async def test_fetches_order_and_valuation_symbols_once(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "bitmart"
        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDT")
        portfolio_content = _portfolio_content()
        _wire_portfolio_pipeline(exchange_manager, portfolio_content)
        open_order = _open_order_dict("order-1", "ETH/USDT")
        fetch_tickers_mock = mock.AsyncMock(return_value={
            "ETH/USDT": {trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 3000},
            "BTC/USDT": {trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 50000},
        })
        with (
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "ensure_temporary_ticker_channel",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                trading_api,
                "get_portfolio",
                return_value=portfolio_content,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_valuation_symbols_from_portfolio",
                side_effect=[["BTC/USDT"], ["BTC/USDT"]],
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_fetch_tickers",
                fetch_tickers_mock,
            ),
            mock.patch.object(
                exchange_account_refresh_module,
                "_refresh_portfolio_valuation",
                mock.AsyncMock(),
            ),
        ):
            await exchange_account_refresh_module.refresh_exchange_account(
                exchange_manager,
                protocol_models.TradingType.SPOT,
                set(),
                is_simulated=True,
                previous_open_orders=[open_order],
            )

        fetch_tickers_mock.assert_awaited_once()
        fetched_symbols = fetch_tickers_mock.await_args.args[1]
        assert set(fetched_symbols) == {"BTC/USDT", "ETH/USDT"}
