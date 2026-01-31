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
import octobot_trading.enums as enums
import typing


async def inner_test_initialize_without_kwargs(order, status: enums.OrderStatus, mocked_method_name: typing.Optional[str]):
    order.status = status
    order.exchange_manager.is_backtesting = True
    pre_call_states = []
    if mocked_method_name is not None:
        async def _side_effect(*args, **kwargs):
            pre_call_states.append(order.state)
            return await origin_method(*args, **kwargs)

        origin_method = getattr(order, mocked_method_name)
        with mock.patch.object(order, mocked_method_name, mock.AsyncMock(side_effect=_side_effect)) as method_mock:
            await order.initialize()
            method_mock.assert_awaited_once()
    else:
        await order.initialize()
        pre_call_states.append(order.state)
    pre_call_state = pre_call_states[0]
    assert pre_call_state.is_from_exchange_data is False
    assert pre_call_state.enable_associated_orders_creation is True
    assert pre_call_state.is_already_counted_in_available_funds is False
    order.clear()


async def inner_test_initialize_with_kwargs(
    order, status: enums.OrderStatus, 
    mocked_method_name: typing.Optional[str], 
    expected_is_from_exchange_data: bool = True
):
    order.status = status
    order.exchange_manager.is_backtesting = True
    pre_call_states = []
    if mocked_method_name is not None:
        async def _side_effect(*args, **kwargs):
            pre_call_states.append(order.state)
            return await origin_method(*args, **kwargs)

        origin_method = getattr(order, mocked_method_name)
        with mock.patch.object(order, mocked_method_name, mock.AsyncMock(side_effect=_side_effect)) as method_mock:
            await order.initialize(
                is_from_exchange_data=True, enable_associated_orders_creation=False, 
                is_already_counted_in_available_funds=True
            )
            method_mock.assert_awaited_once()
    else:
        await order.initialize(
            is_from_exchange_data=True, enable_associated_orders_creation=False, 
            is_already_counted_in_available_funds=True
        )
        pre_call_states.append(order.state)
    pre_call_state = pre_call_states[0]
    assert pre_call_state.is_from_exchange_data is expected_is_from_exchange_data
    assert pre_call_state.enable_associated_orders_creation is False
    assert pre_call_state.is_already_counted_in_available_funds is True
    order.clear()
