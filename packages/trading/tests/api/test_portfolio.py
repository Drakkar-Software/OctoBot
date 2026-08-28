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

import mock
import octobot_commons.constants as commons_constants
import octobot_trading.api.portfolio as portfolio_api


class TestResolvePortfolioValuationUnit:
    @mock.patch("octobot_trading.api.exchange.get_default_exchange_reference_market", return_value="USDC")
    def test_returns_exchange_default_quote_currency_when_set(self, mock_get_default_reference_market):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        assert portfolio_api.resolve_portfolio_valuation_unit(exchange_manager) == "USDC"
        mock_get_default_reference_market.assert_called_once_with("binance")

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value=commons_constants.DEFAULT_REFERENCE_MARKET,
    )
    def test_falls_back_to_default_reference_market_when_option_missing(
        self, mock_get_default_reference_market,
    ):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        assert (
            portfolio_api.resolve_portfolio_valuation_unit(exchange_manager)
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )
        mock_get_default_reference_market.assert_called_once_with("kraken")
