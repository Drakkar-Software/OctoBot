import logging

from config.cst import *


class Trader:
    def __init__(self, config, exchange):
        self.exchange = exchange
        self.config = config
        self.portfolio = {}
        self.risk = self.config["trader"]["risk"]
        self.logger = logging.getLogger("Trader")

        # Debug
        if self.enabled():
            self.logger.debug("Enabled on " + self.exchange.get_name())
        else:
            self.logger.debug("Disabled on " + self.exchange.get_name())

    def enabled(self):
        if self.config["trader"]["enabled"]:
            return True
        else:
            return False

    def get_risk(self):
        return self.risk

    def get_portfolio(self, currency):
        if currency in self.portfolio:
            return self.portfolio[currency]
        else:
            self.portfolio[currency] = 0
            return self.portfolio[currency]

    # TODO
    def create_order(self, order_type, symbol, quantity, price=None, limit_price=None):
        pass

    def update_portfolio(self, symbol, filled_quantity, filled_price, total_fee, status, side):
        if status:
            currency, market = self.exchange.split_symbol(symbol)

            # update currency
            if currency in self.portfolio:
                if side == TradeOrderSide.BUY:
                    self.portfolio[currency] += filled_quantity
                else:
                    self.portfolio[currency] -= filled_quantity
            else:
                self.portfolio[currency] = filled_quantity

            # update market
            if market in self.portfolio:
                if side == TradeOrderSide.BUY:
                    self.portfolio[market] -= (filled_quantity * filled_price) - total_fee
                else:
                    self.portfolio[market] += (filled_quantity * filled_price) - total_fee
            else:
                self.portfolio[market] = (-filled_quantity * filled_price) - total_fee

            # Only for log purpose
            if side == TradeOrderSide.BUY:
                currency_portfolio_num = "+" + str(self.portfolio[currency])
                market_portfolio_num = "-" + str(self.portfolio[market])
            else:
                currency_portfolio_num = "-" + str(self.portfolio[currency])
                market_portfolio_num = "+" + str(self.portfolio[market])

            self.logger.debug("Portfolio updated | " + currency + " " + currency_portfolio_num
                              + " | " + market + " " + market_portfolio_num)

        else:
            self.logger.warning("ORDER NOT FILLED")
