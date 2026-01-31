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

import octobot_trading.personal_data.portfolios.portfolio_value_holder as portfolio_value_holder


class SpotPortfolioValueHolder(portfolio_value_holder.PortfolioValueHolder):
    def get_holdings_ratio(
        self, currency, traded_symbols_only=False, include_assets_in_open_orders=False, coins_whitelist=None
    ):
        return self._get_holdings_ratio_from_portfolio(currency, traded_symbols_only, include_assets_in_open_orders, coins_whitelist)
