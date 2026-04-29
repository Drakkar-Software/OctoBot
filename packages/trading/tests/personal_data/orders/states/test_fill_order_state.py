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
import os

import octobot_trading.personal_data
import octobot_trading.enums as enums
import pytest

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import sell_limit_order, buy_limit_order, buy_market_order
import tests.personal_data.orders.states as states

pytestmark = pytest.mark.asyncio


async def test_initialize_without_kwargs(sell_limit_order):
    await states.inner_test_initialize_without_kwargs(sell_limit_order, enums.OrderStatus.FILLED, 'on_close')


async def test_initialize_with_kwargs(sell_limit_order):
    await states.inner_test_initialize_with_kwargs(sell_limit_order, enums.OrderStatus.FILLED, 'on_close')


async def test_on_order_refresh_successful(buy_limit_order):
    buy_limit_order.status = enums.OrderStatus.FILLED
    buy_limit_order.exchange_manager.is_backtesting = True
    await buy_limit_order.initialize()
    await buy_limit_order.state.on_refresh_successful()
    assert buy_limit_order.is_closed()
    buy_limit_order.clear()


async def test_constructor_with_partially_filled_status(buy_limit_order):
    # with PARTIALLY_FILLED status
    buy_limit_order.status = enums.OrderStatus.PARTIALLY_FILLED
    state = octobot_trading.personal_data.FillOrderState(buy_limit_order, True)
    assert state.state is enums.OrderStates.FILLING
    assert state.is_pending()
    assert not state.is_filled()
    if not os.getenv('CYTHON_IGNORE'):
        assert state.is_status_pending()
        assert not state.is_status_filled()


async def test_constructor_with_filled_status(sell_limit_order):
    # with FILLED status
    sell_limit_order.status = enums.OrderStatus.FILLED
    state = octobot_trading.personal_data.FillOrderState(sell_limit_order, True)
    assert state.state is enums.OrderStates.FILLED
    assert not state.is_pending()
    assert state.is_filled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_filled()


async def test_constructor_with_closed_status(buy_market_order):
    # with CLOSED status
    buy_market_order.status = enums.OrderStatus.CLOSED
    state = octobot_trading.personal_data.FillOrderState(buy_market_order, True)
    assert state.state is enums.OrderStates.FILLED
    assert not state.is_pending()
    assert state.is_filled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_filled()
