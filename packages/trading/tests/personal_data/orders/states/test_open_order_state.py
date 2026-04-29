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
import octobot_trading.personal_data as personal_data
from octobot_trading.enums import OrderStatus, OrderStates, States
from octobot_trading.personal_data.orders.states.order_state_factory import create_order_state
from tests import event_loop
import octobot_trading.enums as enums
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order
import tests.personal_data.orders.states as states
import pytest

pytestmark = pytest.mark.asyncio


async def test_initialize_without_kwargs(buy_limit_order):
    await states.inner_test_initialize_without_kwargs(buy_limit_order, enums.OrderStatus.OPEN, None)


async def test_initialize_with_kwargs(buy_limit_order):
    await states.inner_test_initialize_with_kwargs(buy_limit_order, enums.OrderStatus.OPEN, None)


async def test_on_order_refresh_successful(buy_limit_order):
    buy_limit_order.exchange_manager.is_backtesting = True
    await buy_limit_order.initialize()
    assert isinstance(buy_limit_order.state, personal_data.OpenOrderState)
    await buy_limit_order.state.on_refresh_successful()
    assert buy_limit_order.state.state is States.OPEN
    buy_limit_order.status = OrderStatus.FILLED
    await buy_limit_order.state.on_refresh_successful()
    assert buy_limit_order.is_filled()
