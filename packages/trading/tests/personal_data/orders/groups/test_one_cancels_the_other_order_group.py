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
import decimal

import mock
import pytest

import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_commons.asyncio_tools as asyncio_tools
from tests.personal_data import DEFAULT_ORDER_SYMBOL
from tests.personal_data.orders.groups import order_mock
from tests.personal_data.orders import created_order
from tests.exchanges import simulated_trader, simulated_exchange_manager
import tests.test_utils.random_numbers as random_numbers


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def oco_group():
    orders_manager = mock.Mock()
    orders_manager.get_order_from_group = mock.Mock()
    return personal_data.OneCancelsTheOtherOrderGroup("name",  orders_manager)


async def test_on_fill(oco_group):
    order = order_mock()
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
         as get_order_from_group_mock:
        await oco_group.on_fill(order)
        order.trader.cancel_order.assert_not_called()
        get_order_from_group_mock.assert_called_once_with(oco_group.name)
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[order])) \
         as get_order_from_group_mock:
        await oco_group.on_fill(order, ignored_orders=["hello"])
        order.trader.cancel_order.assert_not_called()
        get_order_from_group_mock.assert_called_once_with(oco_group.name)
    other_order = order_mock()
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[order,
                                                                                                     other_order])) \
         as get_order_from_group_mock:
        await oco_group.on_fill(order)
        order.trader.cancel_order.assert_not_called()
        other_order.trader.cancel_order.assert_called_once_with(
            other_order, ignored_order=order, wait_for_cancelling=True,
            cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
            force_if_disabled=False
        )
        get_order_from_group_mock.assert_called_once_with(oco_group.name)


async def test_on_fill_no_mock(simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    oco_group = personal_data.OneCancelsTheOtherOrderGroup("name",
                                                           exchange_manager.exchange_personal_data.orders_manager)
    stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss.update(
        price=decimal.Decimal(10),
        quantity=decimal.Decimal(1),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=oco_group,
    )
    sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit.update(
        price=decimal.Decimal(20),
        quantity=decimal.Decimal(1),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=oco_group,
    )

    for order in [stop_loss, sell_limit]:
        order.exchange_manager.is_backtesting = True  # force update_order_status
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
            order
        )
    price_events_manager = stop_loss.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    # stop loss sell order triggers when price is bellow or equal to its trigger price
    price_events_manager.handle_recent_trades(
        [random_numbers.decimal_random_recent_trade(price=decimal.Decimal(9), timestamp=stop_loss.timestamp)]
    )
    # simulate a real-trader order (that is self-managed therefore an exchange update is not required)
    stop_loss.simulated = False

    # fill stop loss and cancel sell limit
    await asyncio_tools.wait_asyncio_next_cycle()
    assert stop_loss.is_filled()
    assert sell_limit.is_cancelled()


async def test_on_cancel(oco_group):
    order = order_mock()
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
         as get_order_from_group_mock:
        await oco_group.on_cancel(order)
        order.trader.cancel_order.assert_not_called()
        get_order_from_group_mock.assert_called_once_with(oco_group.name)
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[order])) \
         as get_order_from_group_mock:
        await oco_group.on_cancel(order, ignored_orders=["hi"])
        order.trader.cancel_order.assert_not_called()
        get_order_from_group_mock.assert_called_once_with(oco_group.name)
        get_order_from_group_mock.reset_mock()
        with pytest.raises(errors.OrderGroupTriggerArgumentError):
            await oco_group.on_cancel(order, ignored_orders=["hi", "ho"])
        order.trader.cancel_order.assert_not_called()
        get_order_from_group_mock.assert_not_called()
    other_order = order_mock()
    with mock.patch.object(oco_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[order,
                                                                                                     other_order])) \
         as get_order_from_group_mock:
        await oco_group.on_cancel(order, ignored_orders=["hi"])
        order.trader.cancel_order.assert_not_called()
        other_order.trader.cancel_order.assert_called_once_with(
            other_order, ignored_order="hi", wait_for_cancelling=True,
            cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
            force_if_disabled=False
        )
        get_order_from_group_mock.assert_called_once_with(oco_group.name)


async def test_oco_adapt_before_order_becoming_active(simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    oco_group = personal_data.OneCancelsTheOtherOrderGroup("name",
                                                           exchange_manager.exchange_personal_data.orders_manager)
    assert isinstance(oco_group.active_order_swap_strategy, personal_data.StopFirstActiveOrderSwapStrategy)
    stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss.update(
        price=decimal.Decimal(10),
        quantity=decimal.Decimal(1),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=oco_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss, decimal.Decimal(10), False),
    )
    sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit.update(
        price=decimal.Decimal(20),
        quantity=decimal.Decimal(1),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=oco_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit, decimal.Decimal(20), True),
    )
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    assert portfolio["BTC"].available == decimal.Decimal(10)
    for order in [stop_loss, sell_limit]:
        order.exchange_manager.is_backtesting = True  # force update_order_status
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
            order
        )
        if order is stop_loss:
            # stop sell limit quantity is not removed from available but stop is
            assert portfolio["BTC"].available == decimal.Decimal(9)
        else:
            assert portfolio["BTC"].available == decimal.Decimal(9)
    assert stop_loss.is_active is True
    assert order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False) == [sell_limit]
    with (mock.patch.object(exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock):
        assert await oco_group.adapt_before_order_becoming_active(sell_limit) == ([stop_loss], oco_group._reverse_active_swap)
        cancel_order_mock.assert_called_once()
        assert stop_loss.is_active is False
        assert not stop_loss.is_cleared()
        assert not sell_limit.is_cleared()
        # stop loss is now inactive as well, could be to update sell limit to come active (done in strategy)
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert len(inactive_orders) == 2
        assert stop_loss in inactive_orders and sell_limit in inactive_orders


async def test_oco_reverse_active_swap(oco_group):
    order_1 = mock.Mock()
    order_2 = mock.Mock()
    to_activate_orders = [order_1, order_2]
    with mock.patch.object(oco_group, "adapt_before_order_becoming_active", mock.AsyncMock()) as adapt_before_order_becoming_active_mock, \
        mock.patch.object(order_util, "create_as_active_order_on_exchange", mock.AsyncMock()) as create_as_active_order_on_exchange_mock:
        await oco_group._reverse_active_swap("plop", to_activate_orders)
        assert adapt_before_order_becoming_active_mock.call_count == 2
        assert create_as_active_order_on_exchange_mock.call_count == 2
        assert adapt_before_order_becoming_active_mock.mock_calls[0].args == (order_1,)
        assert adapt_before_order_becoming_active_mock.mock_calls[1].args == (order_2,)
        assert create_as_active_order_on_exchange_mock.mock_calls[0].args == (order_1, False)
        assert create_as_active_order_on_exchange_mock.mock_calls[1].args == (order_2, False)
