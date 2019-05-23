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
from octobot_trading.orders.stop_loss_limit_order import StopLossLimitOrder
from octobot_trading.orders.stop_loss_order import StopLossOrder

from config import OrderStatus, ExchangeConstantsOrderColumns
from octobot_commons.logging.logging_util import get_logger


class OrdersManager:
    _MAX_ORDERS_COUNT = 20000
    """ OrdersManager class will perform the supervision of each open order of the exchange trader
    Data updating process is generic but a specific implementation is called for each type of order
    (TraderOrderTypeClasses)
    The task will perform this data update and the open orders status check each ORDER_REFRESHER_TIME seconds
    This class is particularly needed when exchanges doesn't offer stop loss orders
    This class has an essential role for the trader simulator """

    def __init__(self, config, trader, exchange_manager):
        self.config: dict = config
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.exchange
        self.trader = trader
        self.orders: dict = {}
        self.logger = get_logger(f"{self.__class__.__name__} [{self.exchange.get_name()}]")

    async def initialize(self):
        pass

    def has_order(self, order):
        return order.order_id in self.orders

    def upsert_orders(self, orders):
        for order in orders:
            self.upsert_order(order[ExchangeConstantsOrderColumns.ID.value], order)

    def upsert_order(self, order_id, ccxt_order):
        self.orders[order_id] = ccxt_order
        if len(self.orders) > self._MAX_ORDERS_COUNT:
            self.remove_oldest_orders(int(self._MAX_ORDERS_COUNT / 2))

    def update_order_attribute(self, order_id, key, value):
        self.orders[order_id][key] = value

    def remove_oldest_orders(self, nb_to_remove):
        time_sorted_orders = sorted(self.orders.values(),
                                    key=lambda x: x[ExchangeConstantsOrderColumns.TIMESTAMP.value])
        shrinked_list = [time_sorted_orders[i]
                         for i in range(0, nb_to_remove)
                         if (time_sorted_orders[i][ExchangeConstantsOrderColumns.STATUS.value] ==
                             OrderStatus.OPEN.value
                             or time_sorted_orders[i][ExchangeConstantsOrderColumns.STATUS.value]
                             == OrderStatus.PARTIALLY_FILLED.value)]

        shrinked_list += [time_sorted_orders[i] for i in range(nb_to_remove, len(time_sorted_orders))]
        self.orders = {order[ExchangeConstantsOrderColumns.ID.value]: order for order in shrinked_list}

    def get_all_orders(self, symbol=None, since=None, limit=None) -> list:
        return self._select_orders(None, symbol, since, limit)

    def get_open_orders(self, symbol=None, since=None, limit=None) -> list:
        return self._select_orders(OrderStatus.OPEN.value, symbol, since, limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None) -> list:
        return self._select_orders(OrderStatus.CLOSED.value, symbol, since, limit)

    def get_order(self, order_id):
        return self.orders[order_id]

    def add_order_to_list(self, order):
        if self.should_add_order(order):
            self.orders[order.order_id] = order
            self.logger.debug(f"Order added to open orders (total: {len(self.orders)} open order"
                              f"{'s' if len(self.orders) > 1 else ''})")
        else:
            self.logger.debug(f"Order not added to open orders (already in open order: {self.has_order(order)}) "
                              f"(total: {len(self.orders)} open order{'s' if len(self.orders) > 1 else ''})")

    def should_add_order(self, order):
        return not self.has_order(order) and \
               (self.exchange_manager.is_trader_simulated or not self._already_has_real_or_linked_order(order))

    def _already_has_real_or_linked_order(self, order):
        if order.order_id is not None:
            return self.has_order(order.order_id)
        return (isinstance(order, (StopLossLimitOrder, StopLossOrder)) and
                self._already_an_order_linked_to_these_real_orders(order.linked_orders))

    def _already_an_order_linked_to_these_real_orders(self, linked_orders):
        target_linked_ids = set(linked.get_id() for linked in linked_orders)
        return \
            any(order for order in self.orders.values()
                if order.linked_orders and set(linked.get_id() for linked in order.linked_orders) == target_linked_ids)

    def get_orders_with_symbol(self, symbol):
        return [order for order in self.orders.values() if order.symbol == symbol]

    def remove_order_from_list(self, order):
        """
        Remove the specified order of the current open_order list (when the order is filled or canceled)
        """
        try:
            if self.has_order(order):
                self.orders.pop(order.order_id)
                self.logger.debug(f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()}) "
                                  f"removed on {self.exchange.get_name()}")
            else:
                self.logger.warning(f"Trying to remove order from order manager which is not in order_manager list: "
                                    f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()} "
                                    f"on {self.exchange.get_name()}")
        except Exception as e:
            self.logger.error(str(e))
            self.logger.exception(e)

    # private methods
    def _select_orders(self, state, symbol, since, limit) -> list:
        orders = [
            order
            for order in self.orders.values()
            if (
                    (state is None or order[ExchangeConstantsOrderColumns.STATUS.value] == state) and
                    (symbol is None or (symbol and order[ExchangeConstantsOrderColumns.SYMBOL.value] == symbol)) and
                    (since is None or (since and order[ExchangeConstantsOrderColumns.TIMESTAMP.value] < since))
            )
        ]
        if limit is not None:
            return orders[0:limit]
        return orders

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
    async def force_update_order_status(self, blocking=True, simulated_time=False):
        if blocking:
            return await self._update_orders_status(simulated_time=simulated_time)
        else:
            raise NotImplementedError("force_update_order_status(blocking=False) not implemented")

    async def _update_order_status(self, order, failed_order_updates, simulated_time=False):
        order_filled = False
        try:
            await order.update_order_status(simulated_time=simulated_time)

            if order.get_status() == OrderStatus.FILLED:
                order_filled = True
                self.logger.info(f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()})"
                                 f" filled on {self.trader.get_exchange().get_name()} "
                                 f"at {order.get_filled_price()}")
                await order.close_order()
        except MissingOrderException as e:
            self.logger.error(f"Missing exchange order when updating order with id: {e.order_id}. "
                              f"Will force a real trader refresh. ({e})")
            failed_order_updates.append(e.order_id)
        except InsufficientFunds as e:
            self.logger.error(f"Not enough funds to create order: {e} (updating {order}).")
        return order_filled

    async def _update_orders_status(self, simulated_time=False):
        """
        Prepare order status updating by getting price data
        then ask orders to check their status
        Finally ask cancellation and filling process if it is required
        """

        failed_order_updates = []
        # update all prices
        await self._update_last_symbol_list(True)

        for order in copy.copy(self.order_list):

            order_filled = False
            try:
                # ask orders to update their status
                async with order.get_lock():
                    odr = order
                    # update symbol prices from exchange
                    if odr.get_order_symbol() in self.last_symbol_prices:
                        odr.set_last_prices(self.last_symbol_prices[odr.get_order_symbol()])

                    if odr in self.order_list:
                        order_filled = await self._update_order_status(odr, failed_order_updates, simulated_time)
            except Exception as e:
                raise e
            finally:
                # ensure always call fill callback
                if order_filled:
                    await self.trader.call_order_update_callback(order)
        return failed_order_updates

    async def poll_update(self):
        """
        Async method that will periodically update orders status with update_orders_status
        Should never be called in backtesting
        """
        while self.keep_running:
            try:
                # call update status
                failed_order_updates = await self._update_orders_status()
                if failed_order_updates:
                    self.logger.info(f"Forcing real trader refresh.")
                    self.trader.force_refresh_orders_and_portfolio()
            except Exception as e:
                self.logger.error(f"Error when updating orders ({e})")
                self.logger.exception(e)

            await asyncio.sleep(self.order_refresh_time)
