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

    # TODO
    def create_order(self, order_type, symbol, quantity, price, limit_price=None):
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

            self.logger.info("Portfolio updated | " + currency + " " + self.portfolio[currency]
                             + " | " + market + " " + self.portfolio[market])

        else:
            self.logger.warning("ORDER NOT FILLED")
