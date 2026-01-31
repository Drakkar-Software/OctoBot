#  Drakkar-Software OctoBot-Trading
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
import decimal
import sortedcontainers

import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.util as util
from octobot_trading.enums import ExchangeConstantsOrderBookInfoColumns as ECOBIC

ORDER_ID_NOT_FOUND = -1
INVALID_PARSED_VALUE = -1


class OrderBookManager(util.Initializable):
    def __init__(self):
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.order_book_initialized: bool = False
        self.asks: sortedcontainers.SortedDict = sortedcontainers.SortedDict()
        self.bids: sortedcontainers.SortedDict = sortedcontainers.SortedDict()
        self.timestamp: float = 0
        self.ask_quantity: float = 0
        self.ask_price: float = 0
        self.bid_quantity: float = 0
        self.bid_price: float = 0

    async def initialize_impl(self):
        self.reset_order_book()

    def reset_order_book(self):
        self.order_book_initialized = False
        self.asks.clear()
        self.bids.clear()
        self.timestamp = 0
        self.ask_quantity, self.ask_price, self.bid_quantity, self.bid_price = 0, 0, 0, 0

    def order_book_ticker_update(self, ask_quantity, ask_price, bid_quantity, bid_price):
        self.ask_quantity, self.ask_price = ask_quantity, ask_price
        self.bid_quantity, self.bid_price = bid_quantity, bid_price

    def handle_new_book(self, orders):
        try:
            self.handle_new_books(asks=orders[ECOBIC.ASKS.value],
                                  bids=orders[ECOBIC.BIDS.value],
                                  timestamp=orders[ECOBIC.TIMESTAMP.value])
        except KeyError:
            self.logger.error("Failed to parse new order book")

    def handle_new_books(self, asks, bids, timestamp=None):
        self.reset_order_book()
        self.handle_book_adds(_convert_price_size_list_to_order(asks, enums.TradeOrderSide.SELL.value))
        self.handle_book_adds(_convert_price_size_list_to_order(bids, enums.TradeOrderSide.BUY.value))
        if timestamp:
            self.timestamp = timestamp
        self.order_book_initialized = True

    def handle_book_adds(self, orders):
        for order in orders:
            try:
                self._handle_book_add(order)
            except KeyError as e:
                self.logger.error(f"Error when adding order to order_book : {e}")

    def handle_book_deletes(self, orders):
        for order in orders:
            try:
                self._handle_book_delete(order)
            except KeyError as e:
                self.logger.error(f"Error when deleting order from order_book : {e}")

    def handle_book_updates(self, orders):
        for order in orders:
            try:
                self._handle_book_update(order)
            except KeyError as e:
                self.logger.error(f"Error when updating order in order_book : {e}")

    def _handle_book_add(self, order):
        # Add buy side orders
        if order[ECOBIC.SIDE.value] == enums.TradeOrderSide.BUY.value:
            bids = self.get_bids(order[ECOBIC.PRICE.value])
            if bids is None:
                bids = [order]
            else:
                bids.append(order)
            self._set_bids(order[ECOBIC.PRICE.value], bids)
            return

        # Add sell side orders
        asks = self.get_asks(order[ECOBIC.PRICE.value])
        if asks is None:
            asks = [order]
        else:
            asks.append(order)
        self._set_asks(order[ECOBIC.PRICE.value], asks)

    def _handle_book_delete(self, order):
        price = decimal.Decimal(order[ECOBIC.PRICE.value])

        # Delete buy side orders
        if order[ECOBIC.SIDE.value] == enums.TradeOrderSide.BUY.value:
            bids = self.get_bids(price)
            if bids is not None:
                bids = [bid_order for bid_order in bids if
                        bid_order[ECOBIC.ORDER_ID.value] != order[ECOBIC.ORDER_ID.value]]
                if len(bids) > 0:
                    self._set_bids(price, bids)
                else:
                    self._remove_bids(price)
            return

        # Delete sell side orders
        asks = self.get_asks(price)
        if asks is not None:
            asks = [ask_order for ask_order in asks if
                    ask_order[ECOBIC.ORDER_ID.value] != order[ECOBIC.ORDER_ID.value]]
            if len(asks) > 0:
                self._set_asks(price, asks)
            else:
                self._remove_asks(price)

    def _handle_book_update(self, order):
        size = decimal.Decimal(order.get(ECOBIC.SIZE.value, INVALID_PARSED_VALUE))
        price = decimal.Decimal(order[ECOBIC.PRICE.value])

        # Update buy side orders
        if order[ECOBIC.SIDE.value] == enums.TradeOrderSide.BUY.value:
            bids = self.get_bids(price)
            order_index = _order_id_index(order[ECOBIC.ORDER_ID.value], bids)
            if bids is None or order_index == ORDER_ID_NOT_FOUND:
                return
            if size != INVALID_PARSED_VALUE:
                bids[order_index][ECOBIC.SIZE.value] = size
            self._set_bids(price, bids)
            return

        # Update sell side orders
        asks = self.get_asks(price)
        order_index = _order_id_index(order[ECOBIC.ORDER_ID.value], asks)
        if asks is None or order_index == ORDER_ID_NOT_FOUND:
            return
        if size != INVALID_PARSED_VALUE:
            asks[order_index][ECOBIC.SIZE.value] = size
        self._set_asks(price, asks)

    def _set_asks(self, price, asks):
        self.asks[price] = asks

    def _set_bids(self, price, bids):
        self.bids[price] = bids

    def _remove_asks(self, price):
        del self.asks[price]

    def _remove_bids(self, price):
        del self.bids[price]

    def get_ask(self):
        return self.asks.peekitem(0)

    def get_bid(self):
        return self.bids.peekitem(-1)

    def get_asks(self, price):
        return self.asks.get(price, None)

    def get_bids(self, price):
        return self.bids.get(price, None)


def _order_id_index(order_id, order_list):
    """
    Return order id index in order list
    :param order_id: the order id to search
    :param order_list: the order list to check
    :return: the order id index in order list if found else ORDER_ID_NOT_FOUND
    """
    if order_list is not None:
        for index, order in enumerate(order_list):
            if order[ECOBIC.ORDER_ID.value] == order_id:
                return index
    return ORDER_ID_NOT_FOUND


def _convert_price_size_list_to_order(price_size_list, side):
    """
    Convert a [price, size] list to the book order format
    :param price_size_list: the list of [price, size]
    :param side: the order side
    :return: the converted list
    """
    return [
        _convert_price_size_to_order(price_size, side)
        for price_size in price_size_list
    ]


def _convert_price_size_to_order(price_size, side):
    """
    Convert a pair of price and size to an order book dict format
    :param price_size: the pair, size pair to convert
    :param side: the order side
    :return: the converted pair dict
    """
    return {
        ECOBIC.SIDE.value: side,
        ECOBIC.PRICE.value: price_size[0],
        ECOBIC.SIZE.value: price_size[1],
        ECOBIC.ORDER_ID.value: None
    }
