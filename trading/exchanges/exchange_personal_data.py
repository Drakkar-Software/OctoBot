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

from config import CONFIG_PORTFOLIO_FREE, CONFIG_PORTFOLIO_USED, CONFIG_PORTFOLIO_TOTAL, OrderStatus, \
    ExchangeConstantsOrderColumns
from tools import get_logger
from trading.trader.orders import StopLossLimitOrder, StopLossOrder


class ExchangePersonalData:
    _MAX_ORDERS_COUNT = 20000

    # note: symbol keys are without /
    def __init__(self, exchange_manager):
        self.logger = get_logger(self.__class__.__name__)
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.exchange
        self.portfolio = {}
        self.orders = {}

        self.portfolio_is_initialized = False
        self.orders_are_initialized = False

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def init_portfolio(self):
        self.portfolio_is_initialized = True

    def init_orders(self):
        self.orders_are_initialized = True

    def get_portfolio_is_initialized(self):
        return self.portfolio_is_initialized

    def get_orders_are_initialized(self):
        return self.orders_are_initialized

    def set_portfolio(self, portfolio):
        self.portfolio = portfolio

    def get_portfolio(self):
        return self.portfolio

    # orders
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

    def get_my_recent_trades(self, symbol, since, limit):
        # TODO
        return None

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
        else:
            return (isinstance(order, (StopLossLimitOrder, StopLossOrder)) and
                    self._already_an_order_linked_to_these_real_orders(order.get_linked_orders()))

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
        else:
            return orders
