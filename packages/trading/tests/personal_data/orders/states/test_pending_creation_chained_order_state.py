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
from octobot_trading.enums import OrderStatus, States
import octobot_trading.enums as enums
from octobot_trading.personal_data.orders.states.order_state_factory import create_order_state
from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order
import pytest
import mock
import tests.personal_data.orders.states as states

pytestmark = pytest.mark.asyncio


async def test_initialize_without_kwargs(buy_limit_order):
    with mock.patch.object(personal_data.OrderState, '_is_synchronization_enabled', mock.Mock(return_value=False)) as is_synchronization_enabled_mock:
        await states.inner_test_initialize_without_kwargs(buy_limit_order, enums.OrderStatus.PENDING_CREATION, None)
        assert is_synchronization_enabled_mock.call_count > 0

async def test_initialize_with_kwargs(buy_limit_order):
    with mock.patch.object(personal_data.OrderState, '_is_synchronization_enabled', mock.Mock(return_value=False)) as is_synchronization_enabled_mock:
        await states.inner_test_initialize_with_kwargs(
            buy_limit_order, enums.OrderStatus.PENDING_CREATION, None, expected_is_from_exchange_data=False
        )
        assert is_synchronization_enabled_mock.call_count > 0

async def test_on_order_refresh_successful(buy_limit_order):
    buy_limit_order.exchange_manager.is_backtesting = True
    buy_limit_order.status = OrderStatus.PENDING_CREATION
    buy_limit_order.is_waiting_for_chained_trigger = True
    await buy_limit_order.initialize()
    assert isinstance(buy_limit_order.state, personal_data.PendingCreationChainedOrderState)
    await buy_limit_order.state.on_refresh_successful()
    assert buy_limit_order.state.state is States.PENDING_CREATION
    buy_limit_order.status = OrderStatus.PENDING_CREATION
    await buy_limit_order.state.on_refresh_successful()
    buy_limit_order.status = OrderStatus.PENDING_CREATION
    assert buy_limit_order.is_created() is False
