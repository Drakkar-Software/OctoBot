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
import octobot_trading.enums as trading_enums


class TestResolvePortfolioValuationUnit:
    def test_returns_exchange_default_quote_currency_when_set(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_option_value.return_value = "USDC"
        assert portfolio_api.resolve_portfolio_valuation_unit(exchange_manager) == "USDC"
        exchange_manager.exchange.get_option_value.assert_called_once_with(
            trading_enums.ExchangeClientOptions.DEFAULT_QUOTE_CURRENCY
        )

    def test_falls_back_to_default_reference_market_when_option_missing(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_option_value.return_value = None
        assert (
            portfolio_api.resolve_portfolio_valuation_unit(exchange_manager)
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )
