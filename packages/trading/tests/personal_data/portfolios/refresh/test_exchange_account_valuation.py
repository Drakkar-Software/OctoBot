#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
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

import decimal

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util_module
import octobot_trading.personal_data.portfolios.refresh.exchange_account_valuation as exchange_account_valuation_module


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
        valuation_symbols = exchange_account_valuation_module.valuation_symbols_from_portfolio(
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
        valuation_symbols = exchange_account_valuation_module.valuation_symbols_from_portfolio(
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
        valuation_symbols = exchange_account_valuation_module.valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            "EUR",
        )
        assert valuation_symbols == ["BTC/EUR"]


class TestRefreshPortfolioValuation:
    def test_syncs_portfolio_value_without_profitability_update(self):
        exchange_manager = mock.Mock()
        portfolio_manager = mock.Mock()
        portfolio_value_holder = mock.Mock()
        portfolio_manager.portfolio_value_holder = portfolio_value_holder
        portfolio_manager.portfolio.portfolio = {}
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        exchange_manager.symbol_exists = mock.Mock(return_value=False)
        with mock.patch.object(
            portfolio_util_module,
            "portfolio_to_float",
            return_value={
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: 1000.0,
                    commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
                },
            },
        ):
            exchange_account_valuation_module.refresh_portfolio_valuation(
                exchange_manager,
                "USDT",
            )

        portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values.assert_called_once_with(
            init_price_fetchers=False,
        )
        exchange_manager.exchange_personal_data.handle_portfolio_profitability_update.assert_not_called()
        portfolio_manager.handle_mark_price_update.assert_not_called()

    def test_applies_ticker_prices_via_update_last_price_not_handle_mark_price_update(self):
        exchange_manager = mock.Mock()
        portfolio_manager = mock.Mock()
        portfolio_value_holder = mock.Mock()
        value_converter = mock.Mock()
        portfolio_value_holder.value_converter = value_converter
        portfolio_manager.portfolio_value_holder = portfolio_value_holder
        portfolio_manager.portfolio.portfolio = {}
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        exchange_manager.symbol_exists = mock.Mock(return_value=False)
        tickers = {
            "BTC/USDT": {
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 50000,
            },
        }
        exchange_account_valuation_module.refresh_portfolio_valuation(
            exchange_manager,
            "USDT",
            tickers=tickers,
            valuation_symbols=["BTC/USDT"],
        )

        value_converter.update_last_price.assert_called_once_with(
            "BTC/USDT",
            decimal.Decimal("50000"),
        )
        portfolio_manager.handle_mark_price_update.assert_not_called()
        portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values.assert_called_once_with(
            init_price_fetchers=False,
        )
