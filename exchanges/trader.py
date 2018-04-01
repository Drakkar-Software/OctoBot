import logging
from enum import Enum


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

    def create_order(self, order_type):
        pass


class TraderOrderType(Enum):
    BUY_MARKET = 1
    BUY_LIMIT = 2
    STOP_LOSS = 3
    SELL_MARKET = 4
    SELL_LIMIT = 5
