import logging
import threading
from time import sleep

import ccxt

from backtesting.backtesting import Backtesting
from config.cst import ORDER_REFRESHER_TIME, OrderStatus

""" OrdersManager class will perform the supervision of each open order of the exchange trader
Data updating process is generic but a specific implementation is called for each type of order (TraderOrderTypeClasses)
The thread will perform this data update and the open orders status check each ORDER_REFRESHER_TIME seconds
This class is particularly needed when exchanges doesn't offer stop loss orders
This class has an essential role for the trader simulator """


class OrdersManager(threading.Thread):
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

    # Remove the specified order of the current open_order list (when the order is filled or canceled)
    def remove_order_from_list(self, order):
        try:
            self.order_list.remove(order)
            self.logger.debug("{0} {1} (ID : {2}) removed on {3}".format(order.get_order_symbol(),
                                                                         order.get_name(),
                                                                         order.get_id(),
                                                                         self.trader.get_exchange().get_name()))
        except ValueError:
            pass

    def stop(self):
        self.keep_running = False

    # Update each open order symbol with exchange data
    def _update_last_symbol_list(self):
        updated = []
        for order in self.order_list:
            if order.get_order_symbol() not in updated:
                try:
                    self._update_last_symbol_prices(order.get_order_symbol())
                except ccxt.base.errors.RequestTimeout as e:
                    self.logger.error(str(e))
                updated.append(order.get_order_symbol())

    # Ask to update a specific symbol with exchange data
    def _update_last_symbol_prices(self, symbol):
        last_symbol_price = self.trader.get_exchange().get_recent_trades(symbol)

        # Check if exchange request failed
        if last_symbol_price is not None:
            self.last_symbol_prices[symbol] = last_symbol_price

    def get_open_orders(self):
        return self.order_list

    """ Threading method that will periodically update the data with update_last_symbol_list
    Then ask orders to check their status
    Finally ask cancellation and filling process if it is required 
    """

    def run(self):
        while self.keep_running:
            # update all prices only if simulate
            if self.trader.simulate:
                self._update_last_symbol_list()

            for order in self.order_list:
                # update symbol prices from exchange only if simulate
                if self.trader.simulate:
                    if order.get_order_symbol() in self.last_symbol_prices:
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

            if not Backtesting.enabled(self.config):
                sleep(ORDER_REFRESHER_TIME)
