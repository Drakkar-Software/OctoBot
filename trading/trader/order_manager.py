import logging
import threading
from time import sleep

from config.cst import ORDER_REFRESHER_TIME, OrderStatus


class OrderManager(threading.Thread):
    def __init__(self, config, trader):
        super().__init__()
        self.config = config
        self.keep_running = True
        self.trader = trader
        self.order_list = []
        self.last_symbol_prices = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_order_to_list(self, order):
        self.order_list.append(order)

    def remove_order_from_list(self, order):
        self.order_list.remove(order)

    def stop(self):
        self.keep_running = False

    def update_last_symbol_list(self):
        updated = []
        for order in self.order_list:
            if order.get_order_symbol() not in updated:
                self.update_last_symbol_prices(order.get_order_symbol())
                updated.append(order.get_order_symbol())

    def update_last_symbol_prices(self, symbol):
        self.last_symbol_prices[symbol] = self.trader.get_exchange().get_recent_trades(symbol)

    def get_open_orders(self):
        return self.order_list

    def run(self):
        while self.keep_running:
            # update all prices only if simulate
            if self.trader.simulate:
                self.update_last_symbol_list()

            for order in self.order_list:
                # update symbol prices from exchange only if simulate
                if self.trader.simulate:
                    order.set_last_prices(self.last_symbol_prices[order.get_order_symbol()])

                # ask orders to update their status
                order.update_order_status()
                if order.get_status() == OrderStatus.FILLED:
                    self.logger.info("Order {0} in {1} filled on {2}".format(order.get_id(),
                                                                             order.get_order_symbol(),
                                                                             self.trader.get_exchange().get_name()))
                    order.close_order()

            sleep(ORDER_REFRESHER_TIME)
