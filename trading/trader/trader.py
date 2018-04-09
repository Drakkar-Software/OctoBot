import logging

from trading.trader.portfolio import Portfolio
from trading.trader.trade import Trade


class Trader:
    def __init__(self, config, exchange):
        self.exchange = exchange
        self.config = config
        self.risk = self.config["trader"]["risk"]
        self.logger = logging.getLogger("Trader")
        self.simulate = False

        self.open_orders = []
        self.trades = []

        self.portfolio = Portfolio(self.config, self)

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

    def get_exchange(self):
        return self.exchange

    def get_portfolio(self):
        return self.portfolio

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        pass

    def notify_order_close(self, order):
        # update portfolio with ended order
        self.portfolio.update_portfolio(order)

        # add to trade history
        self.trades.append(Trade(self.exchange, order))

        # remove order to open_orders
        self.open_orders.remove(order)

    def get_open_orders(self):
        return self.open_orders

    def close_open_orders(self):
        pass

    def update_open_orders(self):
        pass

    def stop_order_listeners(self):
        for order in self.open_orders:
            order.stop()

    def join_order_listeners(self):
        for order in self.open_orders:
            order.join()
