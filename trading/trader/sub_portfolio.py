#  Drakkar-Software OctoBot
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

from trading.trader.portfolio import Portfolio


class SubPortfolio(Portfolio):
    DEFAULT_SUB_PORTFOLIO_PERCENT = 0.5

    def __init__(self, config, trader, parent_portfolio, percent, is_relative=True):
        self.parent_portfolio = parent_portfolio
        self.percent = None
        self.is_relative = is_relative
        self.set_percent(percent)
        super().__init__(config, trader)

    # is called in parent initialize
    async def _load_portfolio(self):
        await self.update_portfolio_balance()

    # overwrite parent update_portfolio_balance
    async def update_portfolio_balance(self):
        if self.is_enabled:
            await self.parent_portfolio.update_portfolio_balance()
            self.update_from_parent()

    def update_from_parent(self):
        # get the current portfolio if percent is relative or if we can't use the origin portfolio
        if self.is_relative or not self.trader.get_trades_manager().get_origin_portfolio():
            balance = self.parent_portfolio.get_portfolio()

        # the percent is applied to the origin portfolio (when not relative)
        else:
            balance = self.trader.get_trades_manager().get_origin_portfolio()

        # calculate for each currency the new quantity
        self.portfolio = {currency: {Portfolio.AVAILABLE: balance[currency][Portfolio.AVAILABLE] * self.percent,
                                     Portfolio.TOTAL: balance[currency][Portfolio.TOTAL] * self.percent}
                          for currency in balance}

    def get_parent_portfolio(self):
        return self.parent_portfolio

    def set_percent(self, percent):
        if percent and percent > 0:
            self.percent = percent
        else:
            self.percent = self.DEFAULT_SUB_PORTFOLIO_PERCENT

    def set_is_relative(self, is_relative):
        self.is_relative = is_relative

    async def update_portfolio(self, order):
        await super().update_portfolio(order)
        await self.parent_portfolio.update_portfolio(order)

    def update_portfolio_available(self, order, is_new_order=False):
        super().update_portfolio_available(order, is_new_order=is_new_order)
        self.parent_portfolio.update_portfolio_available(order, is_new_order=is_new_order)

    def reset_portfolio_available(self, reset_currency=None, reset_quantity=None):
        super().reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)
        self.parent_portfolio.reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)
