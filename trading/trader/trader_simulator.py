import logging

from config.cst import CONFIG_ENABLED_OPTION
from trading.trader.order import OrderConstants
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process
"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
        self.risk = self.config["simulator"]["risk"]
        self.logger = logging.getLogger(self.__class__.__name__)
        self.simulate = True

    def enabled(self):
        if self.config["simulator"][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None, linked_to=None):
        self.logger.info("Order creation : {0} | {1} | Price : {2}".format(symbol, order_type, price))

        # create new order instance
        order_class = OrderConstants.TraderOrderTypeClasses[order_type]
        order = order_class(self)
        order.new(order_type, symbol, quantity, price, stop_price)

        # notify order manager of a new open order
        self.order_manager.add_order_to_list(order)

        # update the availability of the currency in the portfolio
        self.portfolio.update_portfolio_available(order, True)

        # if this order is linked to another (ex : a sell limit order with a stop loss order)
        if linked_to is not None:
            linked_to.add_linked_order(order)
            order.add_linked_order(linked_to)

        return order
