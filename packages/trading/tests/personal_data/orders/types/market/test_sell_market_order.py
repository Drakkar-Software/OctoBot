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
from tests.personal_data import DEFAULT_ORDER_SYMBOL, DEFAULT_SYMBOL_QUANTITY
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

from octobot_trading.personal_data.orders.states.open_order_state import OpenOrderState
from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import sell_market_order

pytestmark = pytest.mark.asyncio


async def test_sell_market_order_trigger(sell_market_order):
    order_price = decimal_random_price()
    sell_market_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.SELL_MARKET,
    )
    sell_market_order.exchange_manager.is_backtesting = True  # force update_order_status
    await sell_market_order.initialize()
    assert sell_market_order.is_filled()
