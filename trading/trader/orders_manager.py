#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import copy
from functools import partial

from backtesting.backtesting import Backtesting
from config import ORDER_REFRESHER_TIME, OrderStatus, ORDER_REFRESHER_TIME_WS, ExchangeConstantsTickersColumns as eC
from tools.logging.logging_util import get_logger
from trading.trader.order import Order


class OrdersManager:
    """ OrdersManager class will perform the supervision of each open order of the exchange trader
    Data updating process is generic but a specific implementation is called for each type of order (TraderOrderTypeClasses)
    The thread will perform this data update and the open orders status check each ORDER_REFRESHER_TIME seconds
    This class is particularly needed when exchanges doesn't offer stop loss orders
    This class has an essential role for the trader simulator """

    def __init__(self, config, trader):
        self.config = config
        self.keep_running = True
        self.trader = trader
        self.order_list = []
        self.last_symbol_prices = {}
        self.logger = get_logger(self.__class__.__name__)

        if self.trader.get_exchange().is_web_socket_available():
            self.order_refresh_time = ORDER_REFRESHER_TIME_WS
        else:
            self.order_refresh_time = ORDER_REFRESHER_TIME

    def add_order_to_list(self, order):
        if order not in self.order_list and (self.trader.simulate or not self.has_order_id_in_list(order.get_id())):
            self.order_list.append(order)

    def has_order_id_in_list(self, order_id):
        return any([order.get_id() == order_id for order in self.order_list])

    def remove_order_from_list(self, order):
        """
        Remove the specified order of the current open_order list (when the order is filled or canceled)
        """
        try:
            if order in self.order_list:
                self.order_list.remove(order)
                self.logger.debug("{0} {1} (ID : {2}) removed on {3}".format(order.get_order_symbol(),
                                                                             order.get_name(),
                                                                             order.get_id(),
                                                                             self.trader.get_exchange().get_name()))

        except Exception as e:
            self.logger.error(str(e))
            self.logger.exception(e)

    def stop(self):
        self.keep_running = False

    def _update_last_symbol_list(self, uniformize_timestamps=False):
        """
        Update each open order symbol with exchange data
        """
        updated = []
        for order in self.order_list:
            if isinstance(order, Order) and order.get_order_symbol() not in updated:
                self._update_last_symbol_prices(order.get_order_symbol(), uniformize_timestamps)

                updated.append(order.get_order_symbol())

    def _update_last_symbol_prices(self, symbol, uniformize_timestamps=False):
        """
        Ask to update a specific symbol with exchange data
        """

        exchange = self.trader.get_exchange()

        if Backtesting.enabled(self.config):
            last_symbol_price = self.trader.get_exchange().get_recent_trades(symbol)

        # Exchange call when not backtesting
        else:
            last_symbol_price = exchange.get_recent_trades(symbol)
            if uniformize_timestamps and last_symbol_price:
                timestamp_sample = last_symbol_price[0][eC.TIMESTAMP.value]
                if exchange.get_exchange_manager().need_to_uniformize_timestamp(timestamp_sample):
                    for order in last_symbol_price:
                        order[eC.TIMESTAMP.value] = exchange.get_uniform_timestamp(order[eC.TIMESTAMP.value])

        # Check if exchange request failed
        if last_symbol_price:
            self.last_symbol_prices[symbol] = last_symbol_price

    def get_open_orders(self):
        return self.order_list

    def set_order_refresh_time(self, seconds):
        self.order_refresh_time = seconds

    # Currently called by backtesting
    # Will be called by Websocket to perform order status update if new data available
    # TODO : currently blocking, may implement queue if needed
    def force_update_order_status(self, blocking=True, simulated_time=False):
        if blocking:
            self._update_orders_status(simulated_time=simulated_time)
        else:
            raise NotImplementedError("force_update_order_status(blocking=False) not implemented")

    def _update_orders_status(self, simulated_time=False):
        """
        Prepare order status updating by getting price data
        then ask orders to check their status
        Finally ask cancellation and filling process if it is required
        """

        # update all prices
        self._update_last_symbol_list(True)

        for order in copy.copy(self.order_list):
            # symbol prices from exchange
            if order.get_order_symbol() in self.last_symbol_prices:
                with order as odr:
                    odr.set_last_prices(self.last_symbol_prices[odr.get_order_symbol()])

            # ask orders to update their status
            with order as odr:
                if odr in self.order_list:
                    odr.update_order_status(simulated_time=simulated_time)

                    if odr.get_status() == OrderStatus.FILLED:
                        self.logger.info(f"{odr.get_order_symbol()} {odr.get_name()} (ID : {odr.get_id()})"
                                         f" filled on {self.trader.get_exchange().get_name()} "
                                         f"at {odr.get_filled_price()}")
                        odr.close_order()

    def poll_update(self, loop):
        """
        Async method that will periodically update orders status with update_orders_status
        Should never be called in backtesting
        """
        try:
            # call update status
            self._update_orders_status()
        except Exception as e:
            self.logger.error("Error when updating orders")
            self.logger.exception(e)

        loop.call_later(self.order_refresh_time, partial(self.poll_update, loop))
