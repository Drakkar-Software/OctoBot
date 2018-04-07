import logging

from config.cst import *


class Trader:
    def __init__(self, config, exchange):
        self.exchange = exchange
        self.config = config
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

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        if order_type == TraderOrderType.BUY_MARKET:
            pass
        elif order_type == TraderOrderType.BUY_LIMIT:
            pass
        elif order_type == TraderOrderType.SELL_MARKET:
            pass
        elif order_type == TraderOrderType.SELL_LIMIT:
            pass
        elif order_type == TraderOrderType.STOP_LOSS:
            pass
        elif order_type == TraderOrderType.STOP_LOSS_LIMIT:
            pass
