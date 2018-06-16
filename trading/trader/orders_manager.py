import logging
import threading
from time import sleep

from backtesting.backtesting import Backtesting
from config.cst import ORDER_REFRESHER_TIME, OrderStatus, ORDER_REFRESHER_TIME_WS
from trading.trader.order import Order

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
        self.list_lock = threading.RLock()

        if self.trader.get_exchange().is_websocket_available():
            self.order_refresh_time = ORDER_REFRESHER_TIME_WS
        else:
            self.order_refresh_time = ORDER_REFRESHER_TIME

    def add_order_to_list(self, order):
        with self.list_lock:
            if order not in self.order_list and (self.trader.simulate or not self.has_order_id_in_list(order.get_id())):
                self.order_list.append(order)

    def has_order_id_in_list(self, order_id):
        for order in self.order_list:
            if order.get_id() == order_id:
                return True
        return False

    # Remove the specified order of the current open_order list (when the order is filled or canceled)
    def remove_order_from_list(self, order):
        try:
            with self.list_lock:
                if order in self.order_list:
                    self.order_list.remove(order)
                    self.logger.debug("{0} {1} (ID : {2}) removed on {3}".format(order.get_order_symbol(),
                                                                                 order.get_name(),
                                                                                 order.get_id(),
                                                                                 self.trader.get_exchange().get_name()))

        except Exception as e:
            self.logger.error(str(e))

    def stop(self):
        self.keep_running = False

    # Update each open order symbol with exchange data
    def _update_last_symbol_list(self):
        updated = []
        for order in self.order_list:
            if isinstance(order, Order) and order.get_order_symbol() not in updated:
                self._update_last_symbol_prices(order.get_order_symbol())

                updated.append(order.get_order_symbol())

    # Ask to update a specific symbol with exchange data
    def _update_last_symbol_prices(self, symbol):
        last_symbol_price = None

        # optimize exchange simulator calls when backtesting
        if Backtesting.enabled(self.config):
            if self.trader.get_exchange().get_exchange().should_update_recent_trades(symbol):
                last_symbol_price = self.trader.get_exchange().get_recent_trades(symbol)

        # Exchange call when not backtesting
        else:
            last_symbol_price = self.trader.get_exchange().get_recent_trades(symbol)

        # Check if exchange request failed
        if last_symbol_price is not None:
            self.last_symbol_prices[symbol] = last_symbol_price

    def get_open_orders(self):
        return self.order_list

    def set_order_refresh_time(self, seconds):
        self.order_refresh_time = seconds

    # Will be called by Websocket to perform order status update if new data available
    # TODO : currently blocking, may implement queue if needed
    def force_update_order_status(self):
        self._update_orders_status()

    """ prepare order status updating by getting price data
    then ask orders to check their status
    Finally ask cancellation and filling process if it is required
    """

    def _update_orders_status(self):
        # update all prices
        self._update_last_symbol_list()

        with self.list_lock:
            for order in self.order_list:
                # symbol prices from exchange
                if order.get_order_symbol() in self.last_symbol_prices:
                    with order as odr:
                        odr.set_last_prices(self.last_symbol_prices[odr.get_order_symbol()])

                # ask orders to update their status
                with order as odr:
                    odr.update_order_status()

                    if odr.get_status() == OrderStatus.FILLED:
                        self.logger.info("{0} {1} (ID : {2}) filled on {3} at {4}".format(odr.get_order_symbol(),
                                                                                          odr.get_name(),
                                                                                          odr.get_id(),
                                                                                          self.trader.get_exchange().get_name(),
                                                                                          odr.get_filled_price()))
                        odr.close_order()

    # Threading method that will periodically update orders status with update_orders_status
    def run(self):
        while self.keep_running:

            try:
                # call update status
                self._update_orders_status()

            except Exception as e:
                self.logger.error("Error when updating orders: {0}".format(e))

            if not Backtesting.enabled(self.config):
                sleep(self.order_refresh_time)
            else:
                sleep(0)
