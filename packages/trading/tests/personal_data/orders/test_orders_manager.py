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
import copy
import typing
import pytest
import pytest_asyncio
import time

import octobot_trading.personal_data as personal_data
import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.enums as enums

from tests.exchanges import simulated_exchange_manager, simulated_trader

pytestmark = pytest.mark.asyncio


DEFAULT_SYMBOL = "BTC/USDT"
FIRST_TIME = 1631111111.0
SECOND_TIME = 1631111112.0
THIRD_TIME = 1631111113.0
FOURTH_TIME = 1631111114.0
RAW_ORDERS = [
    {
        "id": "1",
        "timestamp": FIRST_TIME,
        "symbol": DEFAULT_SYMBOL,
        "type": "market",
        "timeInForce": "GTC",
        "postOnly": False,
        "side": "buy",
        "price": 50,
        "stopPrice": None,
        "amount": 5.4,
        "cost": None,
        "average": None,
        "filled": 0,
        "remaining": 5.4,
        "status": "closed",  # will not be accessible from orders_manager as it is closed
        "fee": {"cost": 0.03764836, "currency": "USDT"},
    },
    {
        "id": "2",
        "timestamp": SECOND_TIME,
        "symbol": DEFAULT_SYMBOL,
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "side": "buy",
        "price": 50,
        "stopPrice": None,
        "amount": 5.4,
        "cost": None,
        "average": None,
        "filled": 0.0,
        "remaining": 5.4,
        "status": "open",
        "fee": {"cost": 0.03764836, "currency": "USDT"},
    },
    {
        "id": "3",
        "timestamp": THIRD_TIME,
        "symbol": DEFAULT_SYMBOL,
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "side": "buy",
        "price": 60,
        "stopPrice": None,
        "amount": 3.4,
        "cost": None,
        "average": None,
        "filled": 0.0,
        "remaining": 5.4,
        "status": "open",
        "fee": {"cost": 0.03764836, "currency": "USDT"},
        "tag": "test",
    },
    {
        "id": "4",
        "timestamp": FOURTH_TIME,
        "symbol": DEFAULT_SYMBOL,
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "side": "buy",
        "price": 70,
        "stopPrice": None,
        "amount": 3.4,
        "cost": None,
        "average": None,
        "filled": 5.4,
        "remaining": 0.0,
        "status": "open",
        "fee": {"cost": 0.03764836, "currency": "USDT"},
        "tag": "test",
    },
]


@pytest_asyncio.fixture
async def order_and_exchange_managers(simulated_trader) -> typing.Tuple[personal_data.OrdersManager,
                                                                        exchanges.ExchangeManager]:
    config, exchange_manager, trader = simulated_trader
    return exchange_manager.exchange_personal_data.orders_manager, exchange_manager


async def reset_orders_manager(orders_manager, status=None):
    await orders_manager.initialize_impl()
    await _upsert_raw_orders(RAW_ORDERS, orders_manager, status)


async def _upsert_raw_orders(raw_orders, orders_manager: personal_data.OrdersManager, status=None):
    for order in raw_orders:
        order = _get_raw_order(order, status=status)
        await orders_manager.upsert_order_from_raw(order["id"], order, False)


def _get_raw_order(order, status=None):
    order = copy.deepcopy(order)
    order["status"] = status or order["status"]
    return order


async def test_get_order(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(orders_manager)
    order = orders_manager.get_order("2")
    assert order.order_id == "2"


async def test_get_all_orders(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(orders_manager)
    one_order = orders_manager.get_all_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=THIRD_TIME,
        limit=1,
        tag=None,
    )
    assert len(one_order) == 1
    assert one_order[0].order_id == "2"

    two_orders = orders_manager.get_all_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=THIRD_TIME,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(two_orders) == 2
    assert two_orders[0].order_id == "2"
    assert two_orders[1].order_id == "3"

    since_orders = orders_manager.get_all_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(since_orders) == 3
    assert since_orders[0].order_id == "2"
    assert since_orders[1].order_id == "3"
    assert since_orders[2].order_id == "4"

    until_orders = orders_manager.get_all_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=THIRD_TIME,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(until_orders) == 2
    assert until_orders[0].order_id == "2"
    assert until_orders[1].order_id == "3"

    all_orders = orders_manager.get_all_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(all_orders) == 3
    assert all_orders[0].order_id == "2"
    assert all_orders[1].order_id == "3"
    assert all_orders[2].order_id == "4"

    # TODO uncomment once tags are parsed
    # tagged_order = orders_manager.get_all_orders(
    #     symbol=DEFAULT_SYMBOL, since=constants.NO_DATA_LIMIT, until=constants.NO_DATA_LIMIT, limit=constants.NO_DATA_LIMIT, tag="test"
    # )
    # assert len(tagged_order) == 1
    # assert tagged_order[0].order_id == "4"


async def test_get_pending_cancel_orders(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(
        orders_manager, enums.OrderStatus.PENDING_CANCEL.value
    )

    all_orders = orders_manager.get_pending_cancel_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    # simulated pending cancel orders are turned into cancelled orders when initialized therefore not available
    # in orders_manager as their state init is turning them into trades
    assert len(all_orders) == 0

    selectable_order = personal_data.create_order_instance_from_raw(
        exchange_manager.trader, _get_raw_order(RAW_ORDERS[0], enums.OrderStatus.PENDING_CANCEL.value)
    )
    # order is not initialized and therefore not yet closed
    #  can't use ._add_order() as it is cythonized as private
    orders_manager.orders[selectable_order.order_id] = selectable_order
    orders = orders_manager.get_pending_cancel_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(orders) == 1
    assert orders[0] is selectable_order


async def test_get_closed_orders(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(
        orders_manager, enums.OrderStatus.CLOSED.value
    )

    all_orders = orders_manager.get_closed_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    # closed are not available in orders_manager as their state init is turning them into trades
    assert len(all_orders) == 0

    selectable_order = personal_data.create_order_instance_from_raw(
        exchange_manager.trader, _get_raw_order(RAW_ORDERS[0], enums.OrderStatus.CLOSED.value)
    )
    # order is not initialized and therefore not yet closed
    #  can't use ._add_order() as it is cythonized as private
    orders_manager.orders[selectable_order.order_id] = selectable_order
    orders = orders_manager.get_closed_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(orders) == 1
    assert orders[0] is selectable_order


async def test_get_open_orders(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(orders_manager, enums.OrderStatus.OPEN.value)
    one_order = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=THIRD_TIME,
        limit=1,
        tag=None,
    )
    assert len(one_order) == 1
    assert one_order[0].order_id == "2"

    two_orders = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=THIRD_TIME,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(two_orders) == 2
    assert two_orders[0].order_id == "2"
    assert two_orders[1].order_id == "3"

    since_orders = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(since_orders) == 3
    assert since_orders[0].order_id == "2"
    assert since_orders[1].order_id == "3"
    assert since_orders[2].order_id == "4"

    until_orders = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=THIRD_TIME,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(until_orders) == 2
    assert until_orders[0].order_id == "2"
    assert until_orders[1].order_id == "3"

    all_orders = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=constants.NO_DATA_LIMIT,
        until=constants.NO_DATA_LIMIT,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(all_orders) == 3
    assert all_orders[0].order_id == "2"
    assert all_orders[1].order_id == "3"
    assert all_orders[2].order_id == "4"

    # TODO uncomment once tags are parsed
    # tagged_order = orders_manager.get_open_orders(
    #     symbol=DEFAULT_SYMBOL, since=constants.NO_DATA_LIMIT, until=constants.NO_DATA_LIMIT, limit=constants.NO_DATA_LIMIT, tag="test"
    # )
    # assert len(tagged_order) == 1
    # assert tagged_order[0].order_id == "4"


async def test_get_orders_to_cancel_from_policies(order_and_exchange_managers):
    orders_manager, exchange_manager = order_and_exchange_managers
    await reset_orders_manager(orders_manager, enums.OrderStatus.OPEN.value)

    two_orders = orders_manager.get_open_orders(
        symbol=DEFAULT_SYMBOL,
        since=SECOND_TIME,
        until=THIRD_TIME,
        limit=constants.NO_DATA_LIMIT,
        tag=None,
    )
    assert len(two_orders) == 2
    assert orders_manager.get_orders_to_cancel_from_policies(two_orders) == []
    t = time.time()
    two_orders[0].cancel_policy = personal_data.create_cancel_policy(
        personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        {
            "expiration_time": t + 1000
        }
    )
    assert orders_manager.get_orders_to_cancel_from_policies(two_orders) == []
    two_orders[1].cancel_policy = personal_data.create_cancel_policy(
        personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        {
            "expiration_time": t - 1000
        }
    )
    # only the second order should be cancelled
    assert orders_manager.get_orders_to_cancel_from_policies(two_orders) == [two_orders[1]]
    two_orders[0].cancel_policy = personal_data.create_cancel_policy(
        personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        {
            "expiration_time": t - 10000
        }
    )
    # now both orders should be cancelled
    assert orders_manager.get_orders_to_cancel_from_policies(two_orders) == two_orders