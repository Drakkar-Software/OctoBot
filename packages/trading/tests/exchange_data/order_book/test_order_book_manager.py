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
from copy import deepcopy

import pytest
import pytest_asyncio

from octobot_trading.exchange_data.order_book.order_book_manager import OrderBookManager
from octobot_trading.enums import ExchangeConstantsOrderBookInfoColumns as ECOBIC
from octobot_trading.enums import TradeOrderSide
from tests.test_utils.random_numbers import random_price_list, random_price, random_quantity, random_order_book_side
from tests.test_utils.random_numbers import random_timestamp
from tests import event_loop

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def order_book_manager():
    ob_manager = OrderBookManager()
    await ob_manager.initialize()
    return ob_manager


async def test_init(order_book_manager):
    assert not order_book_manager.order_book_initialized
    assert order_book_manager.ask_quantity == 0
    assert order_book_manager.ask_price == 0
    assert order_book_manager.bid_quantity == 0
    assert order_book_manager.bid_price == 0


async def test_reset(order_book_manager):
    order_book_manager.bids = random_price_list(10)
    order_book_manager.bid_price = random_price()
    order_book_manager.bid_quantity = random_price()
    order_book_manager.reset_order_book()
    assert order_book_manager.bids == []
    assert order_book_manager.bid_quantity == 0
    assert order_book_manager.bid_price == 0


async def test_handle_new_books(order_book_manager):
    ts = random_timestamp()
    asks = random_order_book_side(count=100)
    bids = random_order_book_side(count=100)
    order_book_manager.handle_new_books(asks, bids, timestamp=ts)
    assert order_book_manager.order_book_initialized
    assert order_book_manager.timestamp == ts
    assert order_book_manager.get_ask()
    assert order_book_manager.get_bid()


async def test_order_book_ticker_update(order_book_manager):
    b_price = random_price()
    a_price = random_price()
    b_quantity = random_quantity()
    a_quantity = random_quantity()
    order_book_manager.order_book_ticker_update(a_quantity, a_price, b_quantity, b_price)
    assert order_book_manager.ask_quantity == a_quantity
    assert order_book_manager.ask_price == a_price
    assert order_book_manager.bid_quantity == b_quantity
    assert order_book_manager.bid_price == b_price


async def test_handle_new_book(order_book_manager):
    """
    Handle ccxt request
    {
    'bids': [
        [ price, amount ], // [ float, float ]
        [ price, amount ],
        ...
    ],
    'asks': [
        [ price, amount ],
        [ price, amount ],
        ...
    ],
    'timestamp': 1499280391811, // Unix Timestamp in milliseconds (seconds * 1000)
    'datetime': '2017-07-05T18:47:14.692Z', // ISO8601 datetime string with milliseconds
    'nonce': 1499280391811, // an increasing unique identifier of the orderbook snapshot
    }
    """
    ts = random_timestamp()
    asks = random_order_book_side(count=100)
    bids = random_order_book_side(count=100)
    order_book_manager.handle_new_book({
        ECOBIC.ASKS.value: asks,
        ECOBIC.BIDS.value: bids,
        ECOBIC.TIMESTAMP.value: ts
    })
    assert order_book_manager.timestamp == ts
    assert order_book_manager.get_ask()
    assert order_book_manager.get_bid()


async def test_handle_book_adds(order_book_manager):
    order_book_manager.handle_book_adds([
        get_test_order(TradeOrderSide.BUY.value, "1"),
        get_test_order(TradeOrderSide.BUY.value, "2"),
        get_test_order(TradeOrderSide.SELL.value, "3")
    ])
    assert get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert not get_order_at_id_in_order_list("1", order_book_manager.asks)
    assert not get_order_at_id_in_order_list("2", order_book_manager.asks)
    assert not get_order_at_id_in_order_list("3", order_book_manager.bids)
    assert get_order_at_id_in_order_list("3", order_book_manager.asks)
    assert not get_order_at_id_in_order_list("4", order_book_manager.asks)
    order_book_manager.reset_order_book()
    assert not get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert not get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert not get_order_at_id_in_order_list("3", order_book_manager.asks)


async def test_handle_book_deletes(order_book_manager):
    order_2 = get_test_order(TradeOrderSide.BUY.value, "2")
    order_3 = get_test_order(TradeOrderSide.SELL.value, "3")
    order_5 = get_test_order(TradeOrderSide.SELL.value, "5")
    order_book_manager.handle_book_adds([
        get_test_order(TradeOrderSide.BUY.value, "1"),
        order_2,
        order_3,
        get_test_order(TradeOrderSide.SELL.value, "4"),
        order_5
    ])
    assert get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert get_order_at_id_in_order_list("3", order_book_manager.asks)
    assert get_order_at_id_in_order_list("4", order_book_manager.asks)
    assert get_order_at_id_in_order_list("5", order_book_manager.asks)
    order_book_manager.handle_book_deletes([order_5])
    assert get_order_at_id_in_order_list("4", order_book_manager.asks)
    assert not get_order_at_id_in_order_list("5", order_book_manager.asks)
    order_book_manager.handle_book_deletes([order_2, order_3])
    assert get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert not get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert not get_order_at_id_in_order_list("3", order_book_manager.asks)
    assert get_order_at_id_in_order_list("4", order_book_manager.asks)
    assert not get_order_at_id_in_order_list("5", order_book_manager.asks)


async def test_handle_book_updates(order_book_manager):
    order_3 = get_test_order(TradeOrderSide.BUY.value, "3")
    order_3_2 = get_test_order(TradeOrderSide.BUY.value, "3", order_price=order_3[ECOBIC.PRICE.value])
    order_4 = get_test_order(TradeOrderSide.BUY.value, "4")
    order_4_2 = get_test_order(TradeOrderSide.BUY.value, "4", order_price=order_4[ECOBIC.PRICE.value])
    order_6 = get_test_order(TradeOrderSide.SELL.value, "6")
    order_6_2 = get_test_order(TradeOrderSide.SELL.value, "6", order_price=order_6[ECOBIC.PRICE.value])
    order_book_manager.handle_book_adds([
        get_test_order(TradeOrderSide.BUY.value, "1"),
        get_test_order(TradeOrderSide.BUY.value, "2"),
        order_3,
        order_4,
        get_test_order(TradeOrderSide.SELL.value, "5"),
        order_6
    ])

    assert get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert get_order_at_id_in_order_list("3", order_book_manager.bids)
    assert get_order_at_id_in_order_list("4", order_book_manager.bids)
    assert get_order_at_id_in_order_list("5", order_book_manager.asks)
    assert get_order_at_id_in_order_list("6", order_book_manager.asks)
    # unknown order
    order_book_manager.handle_book_updates([get_test_order(TradeOrderSide.SELL.value, "10")])
    assert get_order_at_id_in_order_list("1", order_book_manager.bids)
    assert get_order_at_id_in_order_list("2", order_book_manager.bids)
    assert get_order_at_id_in_order_list("3", order_book_manager.bids)
    assert get_order_at_id_in_order_list("3", order_book_manager.bids) == order_3
    order_3_1 = deepcopy(order_3)
    order_book_manager.handle_book_updates([order_3_2])
    assert get_order_at_id_in_order_list("3", order_book_manager.bids)[ECOBIC.SIZE.value] != order_3_1[ECOBIC.SIZE.value]
    assert get_order_at_id_in_order_list("3", order_book_manager.bids)[ECOBIC.SIZE.value] == order_3_2[ECOBIC.SIZE.value]
    assert get_order_at_id_in_order_list("4", order_book_manager.bids) == order_4
    assert get_order_at_id_in_order_list("6", order_book_manager.asks) == order_6
    order_4_1 = deepcopy(order_4)
    order_6_1 = deepcopy(order_6)
    order_book_manager.handle_book_updates([order_4_2, order_6_2])
    assert get_order_at_id_in_order_list("4", order_book_manager.bids)[ECOBIC.SIZE.value] != order_4_1[ECOBIC.SIZE.value]
    assert get_order_at_id_in_order_list("4", order_book_manager.bids)[ECOBIC.SIZE.value] == order_4_2[ECOBIC.SIZE.value]
    assert get_order_at_id_in_order_list("6", order_book_manager.asks)[ECOBIC.SIZE.value] != order_6_1[ECOBIC.SIZE.value]
    assert get_order_at_id_in_order_list("6", order_book_manager.asks)[ECOBIC.SIZE.value] == order_6_2[ECOBIC.SIZE.value]


def get_test_order(order_side, order_id, order_price=None, order_size=None):
    return {
        ECOBIC.SIDE.value: order_side,
        ECOBIC.SIZE.value: order_size if order_size is not None else random_quantity(),
        ECOBIC.PRICE.value: order_price if order_price is not None else random_price(),
        ECOBIC.ORDER_ID.value: order_id
    }


def get_order_at_id_in_order_list(order_id, order_list):
    for order in order_list.values():
        if order[0][ECOBIC.ORDER_ID.value] == order_id:
            return order[0]
    return None

