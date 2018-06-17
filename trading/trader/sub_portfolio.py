from trading.trader.portfolio import Portfolio


class SubPortfolio(Portfolio):
    DEFAULT_SUB_PORTFOLIO_PERCENT = 0.5

    def __init__(self, config, trader, parent_portfolio, percent, is_relative=True):
        self.parent_portfolio = parent_portfolio
        self.percent = None
        self.is_relative = is_relative
        self.set_percent(percent)
        super().__init__(config, trader)

    # is called in parent __init__
    def _load_portfolio(self):
        self.update_portfolio_balance()

    # overwrite parent update_portfolio_balance
    def update_portfolio_balance(self):
        if self.is_enabled:
            
            self.parent_portfolio.update_portfolio_balance()
            
            # get the current portfolio if percent is relative or if we can't use the origin portfolio
            if self.is_relative or not self.trader.get_trades_manager().get_origin_portfolio():
                balance = self.parent_portfolio.get_portfolio()

            # the percent is applied to the origin portfolio (when not relative)
            else:
                balance = self.trader.get_trades_manager().get_origin_portfolio()

            # calculate for each currency the new quantity
            for currency in balance:
                self.portfolio[currency] = {
                    Portfolio.AVAILABLE: balance[currency][Portfolio.AVAILABLE] * self.percent,
                    Portfolio.TOTAL: balance[currency][Portfolio.TOTAL] * self.percent}

    def get_parent_portfolio(self):
        return self.parent_portfolio

    def set_percent(self, percent):
        if percent and percent > 0:
            self.percent = percent
        else:
            self.percent = self.DEFAULT_SUB_PORTFOLIO_PERCENT

    def set_is_relative(self, is_relative):
        self.is_relative = is_relative

    def update_portfolio(self, order):
        super().update_portfolio(order)
        self.parent_portfolio.update_portfolio(order)

    def update_portfolio_available(self, order, is_new_order=False):
        super().update_portfolio_available(order, is_new_order=is_new_order)
        self.parent_portfolio.update_portfolio_available(order, is_new_order=is_new_order)

    def reset_portfolio_available(self, reset_currency=None, reset_quantity=None):
        super().reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)

        # TODO for parent
        # self.parent_portfolio.reset_portfolio_available(reset_currency=reset_currency, reset_quantity=reset_quantity)
