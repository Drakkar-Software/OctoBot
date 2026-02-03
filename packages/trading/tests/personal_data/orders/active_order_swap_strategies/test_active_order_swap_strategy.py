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
import octobot_trading.personal_data.orders.order_factory as order_factory
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
def swap_strategy():
    return personal_data.ActiveOrderSwapStrategy(
        123, enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value,
    )


async def test_is_priority_order(swap_strategy):
    assert swap_strategy.swap_timeout == 123
    with pytest.raises(NotImplementedError):
        swap_strategy.is_priority_order(None)


async def test_apply_inactive_orders(swap_strategy, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    oco_group = personal_data.OneCancelsTheOtherOrderGroup(
        "name", exchange_manager.exchange_personal_data.orders_manager, active_order_swap_strategy=swap_strategy
    )
    assert oco_group.active_order_swap_strategy is swap_strategy
    swap_strategy.is_priority_order = mock.Mock(side_effect=lambda o: o.order_type is enums.TraderOrderType.STOP_LOSS)
    with mock.patch.object(personal_data.Order, "set_as_inactive", mock.AsyncMock()) as set_as_inactive_mock:
        stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                  trader_instance, side=enums.TradeOrderSide.SELL)
        sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                                   trader_instance, side=enums.TradeOrderSide.SELL)
        buy_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.BUY_LIMIT,
                                   trader_instance, side=enums.TradeOrderSide.SELL)
        await swap_strategy.apply_inactive_orders([stop_loss, sell_limit, buy_limit])
        assert swap_strategy.is_priority_order.call_count == 3
        assert set_as_inactive_mock.call_count == 2

    # Test with trigger_above_by_order_id parameter
    swap_strategy.is_priority_order = mock.Mock(side_effect=lambda o: o.order_type is enums.TraderOrderType.STOP_LOSS)
    with mock.patch.object(personal_data.Order, "set_as_inactive", mock.AsyncMock()) as set_as_inactive_mock, \
         mock.patch.object(personal_data.Order, "update", mock.Mock()) as update_mock:
        stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                  trader_instance, side=enums.TradeOrderSide.SELL)
        stop_loss.trigger_above = False
        stop_loss.order_id = "stop_loss_id"
        stop_loss.get_filling_price = mock.Mock(return_value=decimal.Decimal("100"))
        
        sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                                   trader_instance, side=enums.TradeOrderSide.SELL)
        sell_limit.trigger_above = True
        sell_limit.order_id = "sell_limit_id"
        sell_limit.get_filling_price = mock.Mock(return_value=decimal.Decimal("200"))
        
        buy_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.BUY_LIMIT,
                                   trader_instance, side=enums.TradeOrderSide.SELL)
        buy_limit.trigger_above = False
        buy_limit.order_id = "buy_limit_id"
        buy_limit.get_filling_price = mock.Mock(return_value=decimal.Decimal("300"))
        
        # Test: trigger_above_by_order_id overrides order's trigger_above
        trigger_above_by_order_id = {
            "stop_loss_id": True,  # Override False to True
            "sell_limit_id": False,  # Override True to False
            # buy_limit_id not in dict, should use its own trigger_above (False)
        }
        await swap_strategy.apply_inactive_orders([stop_loss, sell_limit, buy_limit], 
                                                   trigger_above_by_order_id=trigger_above_by_order_id)
        
        # Verify priority order (stop_loss) gets active_trigger with overridden trigger_above=True
        assert update_mock.call_count == 1
        update_call_kwargs = update_mock.call_args[1]
        assert "active_trigger" in update_call_kwargs
        active_trigger = update_call_kwargs["active_trigger"]
        assert active_trigger.trigger_above is True  # Overridden from False to True
        
        # Verify non-priority orders (sell_limit, buy_limit) get set_as_inactive with correct trigger_above
        assert set_as_inactive_mock.call_count == 2
        assert set_as_inactive_mock.call_args_list[0][0][0].trigger_above is False # sell_limit order's trigger_above is overridden from True to False
        assert set_as_inactive_mock.call_args_list[0][0][0].trigger_price == decimal.Decimal("200") # sell_limit order's trigger_price
        assert set_as_inactive_mock.call_args_list[1][0][0].trigger_above is False # buy limit order's trigger_above's origin value
        assert set_as_inactive_mock.call_args_list[1][0][0].trigger_price == decimal.Decimal("300") # buy_limit order's trigger_price

    # Test: trigger_above_by_order_id is None, should use order's trigger_above
    swap_strategy.is_priority_order = mock.Mock(side_effect=lambda o: o.order_type is enums.TraderOrderType.STOP_LOSS)
    with mock.patch.object(personal_data.Order, "set_as_inactive", mock.AsyncMock()) as set_as_inactive_mock, \
         mock.patch.object(personal_data.Order, "update", mock.Mock()) as update_mock:
        stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                  trader_instance, side=enums.TradeOrderSide.SELL)
        stop_loss.trigger_above = True
        stop_loss.order_id = "stop_loss_id"
        stop_loss.get_filling_price = mock.Mock(return_value=decimal.Decimal("100"))
        
        sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                                   trader_instance, side=enums.TradeOrderSide.SELL)
        sell_limit.trigger_above = False
        sell_limit.order_id = "sell_limit_id"
        sell_limit.get_filling_price = mock.Mock(return_value=decimal.Decimal("200"))
        
        await swap_strategy.apply_inactive_orders([stop_loss, sell_limit], 
                                                   trigger_above_by_order_id=None)
        
        # Verify priority order uses its own trigger_above=True
        assert update_mock.call_count == 1
        update_call_kwargs = update_mock.call_args[1]
        active_trigger = update_call_kwargs["active_trigger"]
        assert active_trigger.trigger_above is True  # Uses order's own value
        
        # Verify non-priority order uses its own trigger_above=False
        assert set_as_inactive_mock.call_count == 1
        assert sell_limit.trigger_above is False  # Uses order's own value



async def test_execute_no_reverse(swap_strategy, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    swap_strategy.is_priority_order = mock.Mock(side_effect=lambda o: o.order_type is enums.TraderOrderType.STOP_LOSS)
    stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    # not part of a group
    wait_for_fill_callback = mock.AsyncMock()
    with pytest.raises(NotImplementedError):
        await swap_strategy.execute(stop_loss, wait_for_fill_callback, 0)

    oco_group = personal_data.OneCancelsTheOtherOrderGroup("name",
                                                           exchange_manager.exchange_personal_data.orders_manager)
    stop_loss.update(
        exchange_order_id="stop",
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=oco_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss, decimal.Decimal(8), False),
    )
    # stop_loss is already active
    with pytest.raises(ValueError):
        await swap_strategy.execute(stop_loss, wait_for_fill_callback, 1)

    sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit.update(
        exchange_order_id="limit",
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=oco_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(stop_loss, decimal.Decimal(18), False),
    )

    for order in [stop_loss, sell_limit]:
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)

    assert len(exchange_manager.exchange_personal_data.orders_manager.get_all_orders()) == 2
    assert len(exchange_manager.exchange_personal_data.orders_manager.get_open_orders()) == 2

    exchange_created_order = personal_data.SellLimitOrder(trader_instance)
    exchange_created_order.update(
        exchange_order_id="limit2",
        order_type=enums.TraderOrderType.SELL_LIMIT,
        order_id="base_order_id",
        symbol=DEFAULT_ORDER_SYMBOL,
        quantity=decimal.Decimal("0.8"),
        price=decimal.Decimal("8"),
        status=enums.OrderStatus.FILLED,
        fee={
            enums.FeePropertyColumns.COST.value: 1,
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
        }
    )

    assert exchange_created_order.is_open()
    assert stop_loss.is_open()

    with mock.patch.object(exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock, \
        mock.patch.object(exchange_manager.exchange, "create_order",
                          mock.AsyncMock(return_value=exchange_created_order)) as create_order_mock, \
        mock.patch.object(order_factory, "create_order_instance_from_raw",
                          mock.Mock(return_value=exchange_created_order)) as create_order_instance_from_raw_mock:
            # execution is not reversed: sell limit takes the place of the stop loss
            await swap_strategy.execute(sell_limit, wait_for_fill_callback, None)
            cancel_order_mock.assert_called_once()
            assert cancel_order_mock.mock_calls[0].args[0] == stop_loss.exchange_order_id
            create_order_mock.assert_called_once()
            assert create_order_mock.mock_calls[0].kwargs["order_type"] == sell_limit.order_type
            create_order_instance_from_raw_mock.assert_called_once()
            assert create_order_instance_from_raw_mock.mock_calls[0].args[1] is exchange_created_order
            assert exchange_created_order.is_closed()
            assert stop_loss.is_closed()
            assert exchange_manager.exchange_personal_data.orders_manager.get_all_orders() == []
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []


async def test_execute_with_reverse(swap_strategy, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    swap_strategy.is_priority_order = mock.Mock(
        side_effect=lambda o: o.order_type is enums.TraderOrderType.STOP_LOSS)
    stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    # not part of a group
    wait_for_fill_callback = mock.AsyncMock()
    with pytest.raises(NotImplementedError):
        await swap_strategy.execute(stop_loss, wait_for_fill_callback, None)

    oco_group = personal_data.OneCancelsTheOtherOrderGroup("name",
                                                           exchange_manager.exchange_personal_data.orders_manager)
    stop_loss.update(
        exchange_order_id="stop",
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=oco_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss, decimal.Decimal(8), False),
    )
    # stop_loss is already active
    with pytest.raises(ValueError):
        await swap_strategy.execute(stop_loss, wait_for_fill_callback, 3)

    sell_limit = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit.update(
        exchange_order_id="limit",
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=oco_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit, decimal.Decimal(18), False),
    )

    for order in [stop_loss, sell_limit]:
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)

    assert len(exchange_manager.exchange_personal_data.orders_manager.get_all_orders()) == 2
    assert len(exchange_manager.exchange_personal_data.orders_manager.get_open_orders()) == 2

    exchange_created_order = personal_data.SellLimitOrder(trader_instance)
    exchange_created_order.update(
        exchange_order_id="limit2",
        order_type=enums.TraderOrderType.SELL_LIMIT,
        order_id="base_order_id",
        symbol=DEFAULT_ORDER_SYMBOL,
        quantity=decimal.Decimal("0.8"),
        price=decimal.Decimal("8"),
        status=enums.OrderStatus.OPEN,
        fee={
            enums.FeePropertyColumns.COST.value: 1,
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
        }
    )

    assert exchange_created_order.is_open()
    assert stop_loss.is_open()

    with mock.patch.object(exchange_manager.exchange, "cancel_order",
                           mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock, \
            mock.patch.object(exchange_manager.exchange, "create_order",
                              mock.AsyncMock(return_value=exchange_created_order)) as create_order_mock, \
            mock.patch.object(order_factory, "create_order_instance_from_raw",
                              mock.Mock(
                                  return_value=exchange_created_order)) as create_order_instance_from_raw_mock:
            # execution is reversed: stop loss is re-created
            await swap_strategy.execute(sell_limit, wait_for_fill_callback, 5)
            assert cancel_order_mock.call_count == 2
            assert cancel_order_mock.mock_calls[0].args[0] == stop_loss.exchange_order_id
            assert cancel_order_mock.mock_calls[1].args[0] == exchange_created_order.exchange_order_id
            assert create_order_mock.call_count == 2
            assert create_order_mock.mock_calls[0].kwargs["order_type"] == sell_limit.order_type
            assert create_order_mock.mock_calls[1].kwargs["order_type"] == stop_loss.order_type
            assert create_order_instance_from_raw_mock.call_count == 2
            assert exchange_created_order.is_open()
            assert stop_loss.is_closed()
            assert len(exchange_manager.exchange_personal_data.orders_manager.get_all_orders()) == 2
            assert len(exchange_manager.exchange_personal_data.orders_manager.get_open_orders()) == 2


async def test_on_order_update(swap_strategy):
    # Setup
    order = mock.Mock()
    order.active_trigger = mock.Mock()
    order.is_synchronization_enabled = mock.Mock(return_value=True)
    order.get_filling_price = mock.Mock(return_value=decimal.Decimal("100"))
    update_time = 1234.56

    # Test with default trigger price configuration (FILLING_PRICE)
    swap_strategy.on_order_update(order, update_time)

    # Verify
    order.active_trigger.update.assert_called_once_with(
        trigger_price=decimal.Decimal("100"),
        min_trigger_time=update_time,
        update_event=True
    )

    # Test with no active trigger
    order.active_trigger = None
    swap_strategy.on_order_update(order, update_time)
    # Should not raise any error when there's no active trigger

    # Test with ORDER_PARAMS_ONLY configuration
    strategy = personal_data.ActiveOrderSwapStrategy(
        trigger_price_configuration=enums.ActiveOrderSwapTriggerPriceConfiguration.ORDER_PARAMS_ONLY.value
    )
    order.active_trigger = mock.Mock()
    order.active_trigger.trigger_price = decimal.Decimal("150")

    strategy.on_order_update(order, update_time)

    # Verify
    order.active_trigger.update.assert_called_once_with(
        trigger_price=decimal.Decimal("150"),
        min_trigger_time=update_time,
        update_event=True
    )
