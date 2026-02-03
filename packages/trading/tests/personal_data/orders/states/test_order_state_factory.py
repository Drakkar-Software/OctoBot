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
import mock
import octobot_trading.personal_data as personal_data
from octobot_trading.enums import OrderStatus, OrderStates, States
from octobot_trading.personal_data.orders import create_order_state

import pytest
from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order

pytestmark = pytest.mark.asyncio

async def test_create_order_state_pending_creation_disable_associated_orders_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.PENDING_CREATION
    with mock.patch.object(personal_data.PendingCreationOrderState, "_synchronize_with_exchange", mock.AsyncMock()) as \
        _synchronize_with_exchange_mock:
        await create_order_state(buy_limit_order, enable_associated_orders_creation=False)
        _synchronize_with_exchange_mock.assert_called_once()
        assert isinstance(buy_limit_order.state, personal_data.PendingCreationOrderState)
        assert buy_limit_order.state.state is States.PENDING_CREATION
        assert buy_limit_order.state.enable_associated_orders_creation is False


async def test_create_order_state_pending_chained_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.PENDING_CREATION
    buy_limit_order.is_waiting_for_chained_trigger = True
    await create_order_state(buy_limit_order)
    assert isinstance(buy_limit_order.state, personal_data.PendingCreationChainedOrderState)
    assert buy_limit_order.state.state is States.PENDING_CREATION
    assert buy_limit_order.state.enable_associated_orders_creation is True  # default value


async def test_create_order_state_open(buy_limit_order):
    buy_limit_order.status = OrderStatus.OPEN
    await create_order_state(buy_limit_order)
    assert isinstance(buy_limit_order.state, personal_data.OpenOrderState)
    assert buy_limit_order.state.state is States.OPEN
    assert buy_limit_order.state.enable_associated_orders_creation is True  # default value


async def test_create_order_state_open_disable_associated_orders_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.OPEN
    await create_order_state(buy_limit_order, enable_associated_orders_creation=False)
    assert isinstance(buy_limit_order.state, personal_data.OpenOrderState)
    assert buy_limit_order.state.state is States.OPEN
    assert buy_limit_order.state.enable_associated_orders_creation is False


async def test_create_order_state_cancel(buy_limit_order):
    buy_limit_order.status = OrderStatus.CANCELED
    await create_order_state(buy_limit_order, enable_associated_orders_creation=True)
    # can be CANCELED or instant CLOSED
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state in [OrderStates.FILLED, States.CLOSED]
    assert buy_limit_order.state.enable_associated_orders_creation is True


async def test_create_order_state_cancel_disable_associated_orders_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.CANCELED
    await create_order_state(buy_limit_order, enable_associated_orders_creation=False)
    # can be CANCELED or instant CLOSED
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state in [OrderStates.FILLED, States.CLOSED]
    assert buy_limit_order.state.enable_associated_orders_creation is False


async def test_create_order_state_fill(buy_limit_order):
    buy_limit_order.status = OrderStatus.FILLED
    await create_order_state(buy_limit_order)
    # can be FILLED or instant CLOSED
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state in [OrderStates.FILLED, States.CLOSED]


async def test_create_order_state_fill_disable_associated_orders_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.FILLED
    await create_order_state(buy_limit_order, enable_associated_orders_creation=False)
    # can be FILLED or instant CLOSED
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state in [OrderStates.FILLED, States.CLOSED]
    assert buy_limit_order.state.enable_associated_orders_creation is False


async def test_create_order_state_close(buy_limit_order):
    buy_limit_order.status = OrderStatus.CLOSED
    await create_order_state(buy_limit_order)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state is States.CLOSED
    assert buy_limit_order.state.enable_associated_orders_creation is True


async def test_create_order_state_close_disable_associated_orders_creation(buy_limit_order):
    buy_limit_order.status = OrderStatus.CLOSED
    await create_order_state(buy_limit_order, enable_associated_orders_creation=False)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.state is States.CLOSED
    assert buy_limit_order.state.enable_associated_orders_creation is False


async def test_create_order_state_fill_to_open_without_ignore(buy_limit_order):
    buy_limit_order.status = OrderStatus.FILLED
    await create_order_state(buy_limit_order)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    buy_limit_order.status = OrderStatus.OPEN
    await create_order_state(buy_limit_order, ignore_states=[])
    assert isinstance(buy_limit_order.state, personal_data.OpenOrderState)
    assert buy_limit_order.state.state is States.OPEN


async def test_create_order_state_fill_to_open_with_ignore(buy_limit_order):
    buy_limit_order.status = OrderStatus.FILLED
    await create_order_state(buy_limit_order, enable_associated_orders_creation=True)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    assert buy_limit_order.state.enable_associated_orders_creation is True
    buy_limit_order.status = OrderStatus.OPEN
    previous_state = buy_limit_order.state
    await create_order_state(buy_limit_order, ignore_states=[States.OPEN], enable_associated_orders_creation=False)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    # state did not change
    assert buy_limit_order.state is previous_state
    # can be FILLED or instant CLOSED
    assert buy_limit_order.state.state in [OrderStates.FILLED, States.CLOSED]
    assert buy_limit_order.state.enable_associated_orders_creation is True  # still True
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)


async def test_create_order_state_cancel_to_open_with_ignore(buy_limit_order):
    buy_limit_order.status = OrderStatus.CANCELED
    await create_order_state(buy_limit_order)
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    buy_limit_order.status = OrderStatus.OPEN
    await create_order_state(buy_limit_order, ignore_states=[States.OPEN])
    assert isinstance(buy_limit_order.state, personal_data.CloseOrderState)
    # can be CANCELED or instant CLOSED
    assert buy_limit_order.state.state in [OrderStates.CANCELED, States.CLOSED]
    assert buy_limit_order.state.enable_associated_orders_creation is True
