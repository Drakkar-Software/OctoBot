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

import pytest

from octobot_commons.asyncio_tools import wait_asyncio_next_cycle
from octobot_trading.enums import TraderOrderType
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as personal_data

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data import DEFAULT_ORDER_SYMBOL, DEFAULT_SYMBOL_QUANTITY
from tests.personal_data.orders import sell_limit_order
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity, \
    decimal_random_recent_trade

pytestmark = pytest.mark.asyncio


async def test_sell_limit_order_trigger(sell_limit_order):
    order_price = decimal_random_price(min_value=2)
    sell_limit_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.SELL_LIMIT,
    )
    sell_limit_order.exchange_manager.is_backtesting = True  # force update_order_status
    await sell_limit_order.initialize()
    await sell_limit_order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
        sell_limit_order
    )
    price_events_manager = sell_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(max_value=order_price - trading_constants.ONE),
                                     timestamp=sell_limit_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not sell_limit_order.is_filled()
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=order_price,
                                     timestamp=sell_limit_order.timestamp - 1)])
    await wait_asyncio_next_cycle()
    assert not sell_limit_order.is_filled()
    price_events_manager.handle_recent_trades([decimal_random_recent_trade(price=order_price,
                                                                           timestamp=sell_limit_order.timestamp)])

    await wait_asyncio_next_cycle()
    assert sell_limit_order.is_filled()


async def test_sell_limit_order_on_origin_price_change(sell_limit_order):
    order_price = decimal.Decimal(100)
    group = personal_data.OneCancelsTheOtherOrderGroup("name", sell_limit_order.exchange_manager.exchange_personal_data.orders_manager)
    sell_limit_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.SELL_LIMIT,
        group=group,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_order, order_price, True)
    )
    sell_limit_order.exchange_manager.is_backtesting = True  # force update_order_status
    await sell_limit_order.initialize()
    await sell_limit_order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
        sell_limit_order
    )
    price_events_manager = sell_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(max_value=order_price - trading_constants.ONE),
                                     timestamp=sell_limit_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not sell_limit_order.is_filled()
    assert sell_limit_order.active_trigger.trigger_price == decimal.Decimal(100)

    # do not update order price
    order_price = decimal.Decimal(10)
    sell_limit_order.update(
        symbol=sell_limit_order.symbol,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY)
    )
    assert sell_limit_order.active_trigger.trigger_price == decimal.Decimal(100)    # did not change
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(max_value=order_price - trading_constants.ONE),
                                     timestamp=sell_limit_order.timestamp)])
    # order is still not triggered by this price
    await wait_asyncio_next_cycle()
    assert not sell_limit_order.is_filled()

    # update order price
    order_price = decimal.Decimal(10)
    sell_limit_order.update(
        symbol=sell_limit_order.symbol,
        price=order_price
    )
    assert sell_limit_order.active_trigger.trigger_price == decimal.Decimal(10)    # changed
    price_events_manager.handle_recent_trades([
        decimal_random_recent_trade(
            price=decimal.Decimal(20),
            timestamp=sell_limit_order.exchange_manager.exchange.get_exchange_current_time()
        )
    ])
    # order is now triggered by the new price
    await wait_asyncio_next_cycle()
    assert sell_limit_order.is_filled()
