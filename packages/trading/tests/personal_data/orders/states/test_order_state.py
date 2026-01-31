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

from mock import patch, Mock, AsyncMock
import pytest

import octobot_trading.personal_data
import octobot_trading.errors
import octobot_trading.enums as enums

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order, stop_loss_limit_order

pytestmark = pytest.mark.asyncio


async def test_constructor(buy_limit_order):
    # with normal order
    state = octobot_trading.personal_data.OrderState(buy_limit_order, True)
    assert state.order is buy_limit_order

    # with cleared order
    buy_limit_order.state = state
    buy_limit_order.clear()
    with pytest.raises(octobot_trading.errors.InvalidOrderState):
        octobot_trading.personal_data.OrderState(buy_limit_order, True)


async def test_update_calls_synchronize_when_pending_for_buy_limit_order(buy_limit_order):
    buy_limit_order.order_type = enums.TraderOrderType.BUY_LIMIT
    state = octobot_trading.personal_data.OrderState(buy_limit_order, True)
    if os.getenv('CYTHON_IGNORE'):
        return
    with patch.object(state, 'synchronize', new=AsyncMock()) as order_state_synchronize_mock, \
            patch.object(state, 'terminate', new=AsyncMock()) as order_state_terminate_mock:
        await state.update()
        order_state_synchronize_mock.assert_called_once()
        order_state_terminate_mock.assert_not_called()


async def test_update_calls_terminate_when_pending_for_stop_loss_limit_order(stop_loss_limit_order):
    stop_loss_limit_order.order_type = enums.TraderOrderType.STOP_LOSS_LIMIT
    state = octobot_trading.personal_data.OrderState(stop_loss_limit_order, True)
    if os.getenv('CYTHON_IGNORE'):
        return
    with patch.object(state, 'synchronize', new=AsyncMock()) as order_state_synchronize_mock, \
            patch.object(state, 'terminate', new=AsyncMock()) as order_state_terminate_mock:
        await state.update()
        order_state_synchronize_mock.assert_not_called()
        order_state_terminate_mock.assert_called_once()


async def test_update_calls_nothing_when_refreshing(buy_limit_order):
    buy_limit_order.order_type = enums.TraderOrderType.BUY_LIMIT
    state = octobot_trading.personal_data.OrderState(buy_limit_order, True)
    if os.getenv('CYTHON_IGNORE'):
        return
    with patch.object(state, 'synchronize', new=AsyncMock()) as order_state_synchronize_mock, \
            patch.object(state, 'terminate', new=AsyncMock()) as order_state_terminate_mock:
        state.state = enums.States.REFRESHING
        await state.update()
        order_state_synchronize_mock.assert_not_called()
        order_state_terminate_mock.assert_not_called()


async def test_is_created(buy_limit_order):
    buy_limit_order.order_type = enums.TraderOrderType.BUY_LIMIT
    state = octobot_trading.personal_data.OrderState(buy_limit_order, True)
    assert state.is_created() is True


async def test_replace_order(buy_limit_order, stop_loss_limit_order):
    buy_limit_order.order_type = enums.TraderOrderType.BUY_LIMIT
    state = octobot_trading.personal_data.OrderState(buy_limit_order, True)
    buy_limit_order.state = state
    assert state.order is buy_limit_order
    assert buy_limit_order.state is state
    await state.replace_order(stop_loss_limit_order)
    assert state.order is stop_loss_limit_order
    assert stop_loss_limit_order.state is state
    assert buy_limit_order.state is None
