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
from tests.personal_data import DEFAULT_ORDER_SYMBOL, DEFAULT_MARKET_QUANTITY
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_market_order

pytestmark = pytest.mark.asyncio


async def test_buy_market_order_trigger(buy_market_order):
    order_price = decimal_random_price()
    buy_market_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / order_price),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.BUY_MARKET,
    )
    buy_market_order.exchange_manager.is_backtesting = True  # force update_order_status
    await buy_market_order.initialize()
    assert buy_market_order.is_filled()
