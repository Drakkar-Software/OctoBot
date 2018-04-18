import logging
import threading
from time import sleep

import ccxt

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
        self.logger.debug("{0} {1} (ID : {2}) removed on {3}".format(order.get_order_symbol(),
                                                                     order.get_name(),
                                                                     order.get_id(),
                                                                     self.trader.get_exchange().get_name()))

    def stop(self):
        self.keep_running = False

    def update_last_symbol_list(self):
        updated = []
        for order in self.order_list:
            if order.get_order_symbol() not in updated:
                try:
                    self.update_last_symbol_prices(order.get_order_symbol())
                except ccxt.base.errors.RequestTimeout as e:
                    self.logger.error(str(e))
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
                    self.logger.info("{0} {1} (ID : {2}) filled on {3} at {4}".format(order.get_order_symbol(),
                                                                                      order.get_name(),
                                                                                      order.get_id(),
                                                                                      self.trader.get_exchange().get_name(),
                                                                                      order.get_filled_price()))
                    order.close_order()

            sleep(ORDER_REFRESHER_TIME)
