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

import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.portfolio as portfolio_class


class SubPortfolio(portfolio_class.Portfolio):
    DEFAULT_SUB_PORTFOLIO_PERCENT = decimal.Decimal("0.5")

    def __init__(self, config, trader, parent_portfolio, percent, is_relative=True):
        self.parent_portfolio = parent_portfolio
        self.is_relative = is_relative
        self.set_percent(percent)
        super().__init__(config, trader)

    # overwrite parent update_portfolio_balance
    def update_portfolio_from_balance(self, balance, force_replace=True):
        modified = self.parent_portfolio.update_portfolio_from_balance(balance, force_replace=force_replace)
        self.update_from_parent()
        return modified

    def update_from_parent(self): # TODO
        # # get the current portfolio if percent is relative or if we can't use the origin portfolio
        # if self.is_relative or not self.trader.get_trades_manager().get_origin_portfolio():
        #     balance = self.parent_portfolio.get_portfolio()
        #
        # # the percent is applied to the origin portfolio (when not relative)
        # else:
        #     balance = self.trader.get_trades_manager().get_origin_portfolio()
        #
        # # calculate for each currency the new quantity
        # self.portfolio = {currency: {PORTFOLIO_AVAILABLE: balance[currency][PORTFOLIO_AVAILABLE] * self.percent,
        #                              PORTFOLIO_TOTAL: balance[currency][PORTFOLIO_TOTAL] * self.percent}
        #                   for currency in balance}
        pass

    def set_percent(self, percent):
        if percent and percent > constants.ZERO:
            self.percent = percent
        else:
            self.percent = self.DEFAULT_SUB_PORTFOLIO_PERCENT

    def update_portfolio_from_filled_order(self, order):
        super().update_portfolio_from_filled_order(order)
        self.parent_portfolio.update_portfolio_from_filled_order(order)

    def update_portfolio_available(self, order, is_new_order=False):
        super().update_portfolio_available(order, is_new_order=is_new_order)
        self.parent_portfolio.update_portfolio_available(order, is_new_order=is_new_order)

    def reset_portfolio_available(self, reset_currency=None, reset_quantity=None):
        super().reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)
        self.parent_portfolio.reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)
