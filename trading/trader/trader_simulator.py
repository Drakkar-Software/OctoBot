import logging

from config.cst import TraderOrderType
from trading.trader.order import TraderOrderTypeClasses
from trading.trader.trader import Trader


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
        self.risk = self.config["simulator"]["risk"]
        self.logger = logging.getLogger("TraderSimulator")
        self.simulate = True

    def enabled(self):
        if self.config["simulator"]["enabled"]:
            return True
        else:
            return False

    def create_order(self, order_type, symbol, quantity, price=None, limit_price=None):
        self.logger.debug("Order creation : " + str(symbol) + " | " + str(order_type))

        order_class = TraderOrderTypeClasses(order_type).value
        order = order_class(self)
        order.new(order_type, symbol, quantity, price, limit_price)
        order.start()
        self.open_orders.append(order)

