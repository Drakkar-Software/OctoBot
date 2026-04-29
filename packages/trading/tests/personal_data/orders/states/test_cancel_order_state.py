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
from tests.personal_data.orders import sell_limit_order, buy_limit_order, buy_market_order, sell_market_order
import tests.personal_data.orders.states as states

pytestmark = pytest.mark.asyncio


async def test_on_order_refresh_successful(sell_limit_order):
    sell_limit_order.status = enums.OrderStatus.CANCELED
    sell_limit_order.exchange_manager.is_backtesting = True
    await sell_limit_order.initialize()
    await sell_limit_order.state.on_refresh_successful()
    assert sell_limit_order.is_cancelled()
    sell_limit_order.clear()


async def test_initialize_without_kwargs(sell_limit_order):
    await states.inner_test_initialize_without_kwargs(sell_limit_order, enums.OrderStatus.CANCELED, 'on_close')


async def test_initialize_with_kwargs(sell_limit_order):
    await states.inner_test_initialize_with_kwargs(sell_limit_order, enums.OrderStatus.CANCELED, 'on_close')


async def test_constructor_real_order_with_pending_cancel_status(buy_limit_order):
    # with PENDING_CANCEL status
    buy_limit_order.status = enums.OrderStatus.PENDING_CANCEL
    buy_limit_order.simulated = False
    state = octobot_trading.personal_data.CancelOrderState(buy_limit_order, True)
    assert state.state is enums.OrderStates.CANCELING
    assert state.is_pending()
    assert not state.is_canceled()
    if not os.getenv('CYTHON_IGNORE'):
        assert state.is_status_pending()
        assert not state.is_status_cancelled()


async def test_constructor_simulated_order_with_pending_cancel_status(buy_limit_order):
    buy_limit_order.status = enums.OrderStatus.PENDING_CANCEL
    buy_limit_order.simulated = True
    state = octobot_trading.personal_data.CancelOrderState(buy_limit_order, True)
    assert state.state is enums.OrderStates.CANCELED
    assert not state.is_pending()
    assert state.is_canceled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_cancelled()


async def test_constructor_with_cancelled_status(sell_limit_order):
    # with CANCELED status
    sell_limit_order.status = enums.OrderStatus.CANCELED
    state = octobot_trading.personal_data.CancelOrderState(sell_limit_order, True)
    assert state.state is enums.OrderStates.CANCELED
    assert not state.is_pending()
    assert state.is_canceled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_cancelled()


async def test_constructor_with_expired_status(buy_market_order):
    # with EXPIRED status
    buy_market_order.status = enums.OrderStatus.EXPIRED
    state = octobot_trading.personal_data.CancelOrderState(buy_market_order, True)
    assert state.state is enums.OrderStates.CANCELED
    assert not state.is_pending()
    assert state.is_canceled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_cancelled()


async def test_constructor_with_rejected_status(sell_market_order):
    # with REJECTED status
    sell_market_order.status = enums.OrderStatus.REJECTED
    state = octobot_trading.personal_data.CancelOrderState(sell_market_order, True)
    assert state.state is enums.OrderStates.CANCELED
    assert not state.is_pending()
    assert state.is_canceled()
    if not os.getenv('CYTHON_IGNORE'):
        assert not state.is_status_pending()
        assert state.is_status_cancelled()
