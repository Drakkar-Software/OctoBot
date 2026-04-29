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
import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.assets.margin_asset as margin_asset
import octobot_trading.personal_data.portfolios.portfolio as portfolio_class


class MarginPortfolio(portfolio_class.Portfolio):
    def create_currency_asset(self, currency, available=constants.ZERO, total=constants.ZERO):
        return margin_asset.MarginAsset(name=currency, available=available, total=total)

    def update_portfolio_data_from_order(self, order):
        pass  # TODO

    def update_portfolio_data_from_withdrawal(self, amount, currency):
        pass  # TODO

    def update_portfolio_available_from_order(self, order, is_new_order=True):
        pass  # TODO
