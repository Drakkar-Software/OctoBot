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
from typing import Tuple

import pytest

from octobot_commons.asyncio_tools import wait_asyncio_next_cycle

from octobot_trading.exchange_data.prices.price_events_manager import PriceEventsManager
from octobot_trading.enums import TradeOrderType, TradeOrderSide, MarkPriceSources
from octobot_trading.personal_data.orders import TrailingStopOrder
import octobot_trading.constants as trading_constants
from tests.personal_data import DEFAULT_SYMBOL_QUANTITY, DEFAULT_ORDER_SYMBOL, DEFAULT_MARKET_QUANTITY

from tests.test_utils.random_numbers import decimal_random_price, \
    decimal_random_quantity, decimal_random_recent_trade
from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import trailing_stop_order

pytestmark = pytest.mark.asyncio


async def test_trailing_stop_trigger(trailing_stop_order):
    trailing_stop_order, order_price, price_events_manager = await initialize_trailing_stop(trailing_stop_order)
    await trailing_stop_order.set_trailing_percent(decimal.Decimal(10))
    max_trailing_hit_price = get_price_percent(order_price, trailing_stop_order.trailing_percent)

    # set mark price
    set_mark_price(trailing_stop_order, order_price)

    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(
            price=decimal_random_price(min_value=decimal.Decimal(max_trailing_hit_price),
                                       max_value=order_price - trading_constants.ONE),
            timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=order_price,
                                     timestamp=trailing_stop_order.timestamp - 1)])
    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()
    price_events_manager.handle_recent_trades([decimal_random_recent_trade(price=order_price,
                                                                           timestamp=trailing_stop_order.timestamp)])

    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()
    # avoid decimal to float rounding issues
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=max_trailing_hit_price - decimal.Decimal("0.0001"),
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert trailing_stop_order.is_filled()


async def test_trailing_stop_with_new_price(trailing_stop_order):
    trailing_stop_order, order_price, price_events_manager = await initialize_trailing_stop(trailing_stop_order)
    await trailing_stop_order.set_trailing_percent(decimal.Decimal(2))
    new_trailing_price = decimal_random_price(min_value=order_price * decimal.Decimal(str(0.99)),
                                              max_value=order_price * decimal.Decimal(str(1.01)))

    # set mark price
    set_mark_price(trailing_stop_order, new_trailing_price)

    # move trailing price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=new_trailing_price,
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()

    # test fill stop loss with new order price reference
    # avoid decimal to float rounding issues
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=get_price_percent(new_trailing_price - decimal.Decimal("0.0001"),
                                                             trailing_stop_order.trailing_percent),
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert trailing_stop_order.is_filled()


async def test_trailing_stop_with_new_old_price(trailing_stop_order):
    trailing_stop_order, order_price, price_events_manager = await initialize_trailing_stop(trailing_stop_order)
    await trailing_stop_order.set_trailing_percent(decimal.Decimal(5))
    new_trailing_price = decimal_random_price(min_value=order_price * decimal.Decimal(str(0.99)),
                                              max_value=order_price * decimal.Decimal(str(1.01)))

    # set mark price
    set_mark_price(trailing_stop_order, new_trailing_price)

    # move trailing price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=new_trailing_price,
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()

    # test fill stop loss with old price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=get_price_percent(order_price - decimal.Decimal("0.0001"),
                                                             trailing_stop_order.trailing_percent),
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert trailing_stop_order.is_filled()


async def test_trailing_stop_with_new_price_inversed(trailing_stop_order):
    trailing_stop_order, order_price, price_events_manager = await initialize_trailing_stop(trailing_stop_order,
                                                                                            side=TradeOrderSide.BUY)
    await trailing_stop_order.set_trailing_percent(decimal.Decimal(5))
    new_trailing_price = decimal_random_price(min_value=order_price * decimal.Decimal(str(0.99)),
                                              max_value=order_price * decimal.Decimal(str(1.01)))

    # set mark price
    set_mark_price(trailing_stop_order, new_trailing_price)

    # move trailing price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=new_trailing_price,
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not trailing_stop_order.is_filled()

    # test fill stop loss with new order price reference
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=get_price_percent(new_trailing_price + decimal.Decimal("0.0001"),
                                                             trailing_stop_order.trailing_percent,
                                                             selling_side=False),
                                     timestamp=trailing_stop_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert trailing_stop_order.is_filled()


async def initialize_trailing_stop(order, side=TradeOrderSide.SELL) -> Tuple[
    TrailingStopOrder, decimal.Decimal, PriceEventsManager]:
    order_price = decimal_random_price()
    order_max_quantity = DEFAULT_SYMBOL_QUANTITY \
        if side is TradeOrderSide.SELL else DEFAULT_MARKET_QUANTITY / order_price
    order.update(
        price=order_price,
        # divide quantity by 2 to prevent trailing price movement to impact usable quantity
        quantity=decimal_random_quantity(max_value=order_max_quantity / decimal.Decimal(2)),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TradeOrderType.TRAILING_STOP,
    )
    order.side = side
    order.exchange_manager.is_backtesting = True  # force update_order_status
    await order.initialize()
    price_events_manager = order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)
    return order, order_price, price_events_manager


def get_price_percent(price, percent, selling_side=True):
    return price * (1 + (percent / 100) * (-1 if selling_side else 1))


def set_mark_price(order, mark_price):
    prices_manager = order.exchange_manager.exchange_symbols_data. \
        get_exchange_symbol_data(order.symbol).prices_manager
    prices_manager.set_mark_price(decimal.Decimal(mark_price), MarkPriceSources.EXCHANGE_MARK_PRICE.value)
    prices_manager.mark_price_set_time = order.timestamp
