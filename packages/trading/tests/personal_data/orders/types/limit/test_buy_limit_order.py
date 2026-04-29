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
import pytest

from octobot_trading.enums import TraderOrderType
from octobot_commons.asyncio_tools import wait_asyncio_next_cycle

import octobot_trading.constants as trading_constants
from tests.personal_data import DEFAULT_MARKET_QUANTITY, DEFAULT_ORDER_SYMBOL
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity, \
    decimal_random_recent_trade

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order

pytestmark = pytest.mark.asyncio


async def test_buy_limit_order_trigger(buy_limit_order):
    order_price = decimal_random_price()
    buy_limit_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / order_price),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.BUY_LIMIT,
    )
    buy_limit_order.exchange_manager.is_backtesting = True  # force update_order_status
    await buy_limit_order.initialize()
    await buy_limit_order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
        buy_limit_order
    )
    price_events_manager = buy_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(min_value=order_price + trading_constants.ONE),
                                     timestamp=buy_limit_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not buy_limit_order.is_filled()
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=order_price,
                                     timestamp=buy_limit_order.timestamp - 1)])
    await wait_asyncio_next_cycle()
    assert not buy_limit_order.is_filled()
    price_events_manager.handle_recent_trades([decimal_random_recent_trade(price=order_price,
                                                                           timestamp=buy_limit_order.timestamp)])

    await wait_asyncio_next_cycle()
    assert buy_limit_order.is_filled()
