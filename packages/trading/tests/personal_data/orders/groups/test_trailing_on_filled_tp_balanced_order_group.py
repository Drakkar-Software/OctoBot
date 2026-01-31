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
import asyncio

import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders.order_factory as order_factory
import octobot_trading.personal_data.orders.groups.balanced_take_profit_and_stop_order_group as \
    balanced_take_profit_and_stop_order_group
import octobot_trading.personal_data.orders.groups.trailing_on_filled_tp_balanced_order_group as \
    trailing_on_filled_tp_balanced_order_group
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_util as order_util
from tests.exchanges import backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests.personal_data.orders.groups import order_mock
from tests.personal_data import DEFAULT_ORDER_SYMBOL
from tests.personal_data.orders import created_order
from tests.exchanges import simulated_trader, simulated_exchange_manager


@pytest.fixture
def toftpb_group(backtesting_exchange_manager):
    orders_manager = mock.Mock()
    orders_manager.get_order_from_group = mock.Mock()
    return personal_data.TrailingOnFilledTPBalancedOrderGroup("name",  orders_manager)


@pytest.fixture
def side_balance():
    return balanced_take_profit_and_stop_order_group.SideBalance(None, False)


@pytest.fixture
def trailing_side_balance():
    return trailing_on_filled_tp_balanced_order_group.TrailingSideBalance(None, True)


@pytest.fixture
def order_f():
    trader = mock.Mock(exchange_manager=mock.Mock())
    target_order = personal_data.Order(trader)
    return target_order


def test_balances_factory(toftpb_group):
    closed_orders = []
    filled = False
    balances = toftpb_group._balances_factory(closed_orders, filled)
    assert isinstance(balances[toftpb_group.TAKE_PROFIT], balanced_take_profit_and_stop_order_group.SideBalance)
    assert isinstance(balances[toftpb_group.STOP], trailing_on_filled_tp_balanced_order_group.TrailingSideBalance)


@pytest.mark.asyncio
async def test_trailing_balanced_trail_after_order_fill(simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    exchange_manager.is_backtesting = True  # force update_order_status
    tbtp_group = personal_data.TrailingOnFilledTPBalancedOrderGroup(
        "name", exchange_manager.exchange_personal_data.orders_manager
    )
    assert isinstance(tbtp_group.active_order_swap_strategy, personal_data.StopFirstActiveOrderSwapStrategy)
    stop_loss = created_order(personal_data.StopLossOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss.update(
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.6"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=tbtp_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss, decimal.Decimal(8), False),
        exchange_order_id="e_stop_loss_1"
    )
    stop_loss.trailing_profile = personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price, price, True)
        for price in (20, 30)
    ])
    sell_limit_1 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_1.update(
        price=decimal.Decimal(20),
        quantity=decimal.Decimal("0.4"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=tbtp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_1, decimal.Decimal(20), True),
        exchange_order_id="e_sell_limit_1"
    )
    sell_limit_2 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_2.update(
        price=decimal.Decimal(30),
        quantity=decimal.Decimal("0.2"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=tbtp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_2, decimal.Decimal(30), True),
        exchange_order_id="e_sell_limit_2"
    )
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    assert portfolio["BTC"].available == decimal.Decimal(10)
    locked_amount = constants.ZERO
    for order in [stop_loss, sell_limit_1, sell_limit_2]:
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)
        if order in [stop_loss]:
            # stop sell limit quantity is not removed from available but stop is
            locked_amount += order.origin_quantity
        assert portfolio["BTC"].available == decimal.Decimal(10) - locked_amount
    assert stop_loss.is_active is True
    assert sorted(
        order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False), key=lambda x: x.origin_price
    ) ==  sorted(
        [sell_limit_1, sell_limit_2], key=lambda x: x.origin_price
    )
    assert len(tbtp_group.get_group_open_orders()) == 3
    assert all(order in tbtp_group.get_group_open_orders()
               for order in order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders())

    async def _edit_order(*args, quantity=None, price=None, **kwargs):
        edited_stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                        trader_instance, side=enums.TradeOrderSide.SELL)
        price = price or decimal.Decimal(10)
        edited_stop_loss.update(
            price=price,
            quantity=quantity,
            symbol=DEFAULT_ORDER_SYMBOL,
            order_type=enums.TraderOrderType.STOP_LOSS,
            group=tbtp_group,
            is_active=True,
            active_trigger=personal_data.create_order_price_trigger(edited_stop_loss, price, False),
            exchange_order_id="edited_stop_loss"
        )
        order_dict = edited_stop_loss.to_dict()
        order_dict.pop(enums.ExchangeConstantsOrderColumns.ID.value)
        return order_dict

    with mock.patch.object(exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock, \
            mock.patch.object(exchange_manager.exchange, "edit_order",
                              mock.AsyncMock(side_effect=_edit_order)) as edit_order_mock:
        # STEP 1: filling sell_limit_1
        # sell_limit_1 become active: stop_loss is reduced and remains active
        step_1_maybe_partially_inactive_orders, step_1_reverse = await tbtp_group.adapt_before_order_becoming_active(sell_limit_1)
        sell_limit_1.is_active = True    # simulate now active order
        assert step_1_maybe_partially_inactive_orders == [stop_loss]
        cancel_order_mock.assert_not_called()
        edit_order_mock.assert_called_once()
        assert stop_loss.is_active is True
        for order in [stop_loss, sell_limit_1, sell_limit_2]:
            assert not order.is_cleared()
        all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert len(all_orders) == 3
        assert len(tbtp_group.get_group_open_orders()) == 3
        assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)
        assert stop_loss in all_orders
        assert all(order in all_orders for order in [sell_limit_1, sell_limit_2])
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert len(inactive_orders) == 1
        assert inactive_orders == [sell_limit_2]
        # stop_loss is reduced
        assert stop_loss.origin_quantity == decimal.Decimal("0.2")  # 0.6 - 0.4
        # stop_loss price is still the same (sell order is not filled)
        assert stop_loss.origin_price == decimal.Decimal("8")
        cancel_order_mock.reset_mock()
        edit_order_mock.reset_mock()

        # fill sell_limit_1: stop_loss price trails, no order is cancelled
        await sell_limit_1.on_fill(force_fill=True)
        assert sell_limit_1.is_closed()
        assert not stop_loss.is_closed()
        assert sell_limit_1.is_cleared()
        assert not stop_loss.is_cleared()
        cancel_order_mock.assert_not_called()
        # trailing
        edit_order_mock.assert_called_once()
        assert edit_order_mock.mock_calls[0].args[0] == stop_loss.exchange_order_id
        assert edit_order_mock.mock_calls[0].kwargs["quantity"] == decimal.Decimal("0.2")
        assert edit_order_mock.mock_calls[0].kwargs["price"] == decimal.Decimal("20")
        assert stop_loss.origin_price == decimal.Decimal("20")  # updated price
        assert stop_loss.origin_quantity == decimal.Decimal("0.2")  # same quantity

        all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert len(all_orders) == 2
        assert all(order in all_orders for order in [stop_loss, sell_limit_2])
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert inactive_orders == [sell_limit_2]
        cancel_order_mock.reset_mock()
        edit_order_mock.reset_mock()

        # STEP 2: filling sell_limit_2
        # sell_limit_2 become active: stop loss gets canceled
        step_2_maybe_partially_inactive_orders, step_1_reverse = await tbtp_group.adapt_before_order_becoming_active(sell_limit_2)
        sell_limit_2.is_active = True    # simulate now active order
        assert step_2_maybe_partially_inactive_orders == [stop_loss]
        cancel_order_mock.assert_called_once()
        assert cancel_order_mock.mock_calls[0].args[0] == stop_loss.exchange_order_id
        edit_order_mock.assert_not_called()
        assert sell_limit_2.is_active is True
        assert stop_loss.is_active is False
        for order in [stop_loss, sell_limit_2]:
            assert not order.is_cleared()
        all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert len(all_orders) == 2
        assert len(tbtp_group.get_group_open_orders()) == 2
        assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)
        assert all(order in all_orders for order in [stop_loss, sell_limit_2])
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert inactive_orders == [stop_loss]
        # stop_loss is not reduced
        assert stop_loss.origin_quantity == decimal.Decimal("0.2")
        # stop_loss price is still the same
        assert stop_loss.origin_price == decimal.Decimal("20")
        cancel_order_mock.reset_mock()
        edit_order_mock.reset_mock()

        # fill sell_limit_2: stop_loss is canceled
        await sell_limit_2.on_fill(force_fill=True)
        assert sell_limit_2.is_closed()
        assert stop_loss.is_closed()
        assert sell_limit_2.is_cleared()
        assert stop_loss.is_cleared()
        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert all_orders == []
        cancel_order_mock.assert_not_called()
        edit_order_mock.assert_not_called()
        # did not trail (got canceled instead)
        assert stop_loss.origin_price == decimal.Decimal("20")  # same price
        assert stop_loss.origin_quantity == decimal.Decimal("0.2")  # same quantity

@pytest.mark.asyncio
async def test_trailing_balanced_adapt_before_order_becoming_active_2_simultaneous_orders(simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    exchange_manager.is_backtesting = True  # force update_order_status
    tbtp_group = personal_data.TrailingOnFilledTPBalancedOrderGroup(
        "name", exchange_manager.exchange_personal_data.orders_manager
    )
    assert isinstance(tbtp_group.active_order_swap_strategy, personal_data.StopFirstActiveOrderSwapStrategy)
    stop_loss_1 = created_order(personal_data.StopLossOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss_1.update(
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=tbtp_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss_1, decimal.Decimal(8), False),
        exchange_order_id="e_stop_loss_1"

    )
    stop_loss_2 = created_order(personal_data.StopLossOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss_2.update(
        price=decimal.Decimal(10),
        quantity=decimal.Decimal("0.2"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=tbtp_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss_2, decimal.Decimal(10), False),
        exchange_order_id="e_stop_loss_2"
    )
    updated_stop_loss_2 = [stop_loss_2]
    sell_limit_1 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_1.update(
        price=decimal.Decimal(20),
        quantity=decimal.Decimal("0.4"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=tbtp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_1, decimal.Decimal(20), True),
        exchange_order_id="e_sell_limit_1"
    )
    sell_limit_2 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_2.update(
        price=decimal.Decimal(30),
        quantity=decimal.Decimal("0.2"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=tbtp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_2, decimal.Decimal(30), True),
        exchange_order_id="e_sell_limit_2"
    )
    sell_limit_3 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_3.update(
        price=decimal.Decimal(40),
        quantity=decimal.Decimal("0.4"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=tbtp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_3, decimal.Decimal(40), True),
        exchange_order_id="e_sell_limit_3"
    )
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    assert portfolio["BTC"].available == decimal.Decimal(10)
    locked_amount = constants.ZERO
    for order in [stop_loss_1, stop_loss_2, sell_limit_1, sell_limit_2, sell_limit_3]:
        await order.initialize()
        await order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)
        if order in [stop_loss_1, stop_loss_2]:
            # stop sell limit quantity is not removed from available but stop is
            locked_amount += order.origin_quantity
        assert portfolio["BTC"].available == decimal.Decimal(10) - locked_amount
    assert stop_loss_1.is_active is True
    assert stop_loss_2.is_active is True
    assert sorted(
        order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False), key=lambda x: x.origin_price
    ) ==  sorted(
        [sell_limit_1, sell_limit_2, sell_limit_3], key=lambda x: x.origin_price
    )
    assert len(tbtp_group.get_group_open_orders()) == 5
    assert all(order in tbtp_group.get_group_open_orders()
               for order in order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders())

    async def _edit_order(*args, quantity=None, price=None, **kwargs):
        edited_stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                        trader_instance, side=enums.TradeOrderSide.SELL)
        edited_stop_loss.update(
            price=price or decimal.Decimal(10),
            quantity=quantity,
            symbol=DEFAULT_ORDER_SYMBOL,
            order_type=enums.TraderOrderType.STOP_LOSS,
            group=tbtp_group,
            is_active=True,
            active_trigger=personal_data.create_order_price_trigger(edited_stop_loss, decimal.Decimal(10), False),
            exchange_order_id="edited_stop_loss_1"
        )
        order_dict = edited_stop_loss.to_dict()
        order_dict.pop(enums.ExchangeConstantsOrderColumns.ID.value)
        return order_dict

    with mock.patch.object(exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock, \
            mock.patch.object(exchange_manager.exchange, "edit_order",
                              mock.AsyncMock(side_effect=_edit_order)) as edit_order_mock:
        async def step1_task():
            # STEP 1
            # sell_limit_1 become active: stop_loss_2 is now inactive, stop_loss_1 is reduced and remains active
            step_1_maybe_partially_inactive_orders, step_1_reverse = await tbtp_group.adapt_before_order_becoming_active(sell_limit_1)
            sell_limit_1.is_active = True    # simulate now active order
            assert step_1_maybe_partially_inactive_orders == [stop_loss_2, stop_loss_1]
            cancel_order_mock.assert_called_once()
            edit_order_mock.assert_called_once()
            assert stop_loss_1.is_active is True
            assert stop_loss_2.is_active is False
            for order in [stop_loss_1, stop_loss_2, sell_limit_1, sell_limit_2, sell_limit_3]:
                assert not order.is_cleared()
            # stop_loss_2 is now inactive as well, sell limit could be updated to come active (done in strategy)
            all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
            assert len(all_orders) == 5
            assert len(tbtp_group.get_group_open_orders()) == 5
            assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)
            assert stop_loss_1 in all_orders and stop_loss_2 in all_orders
            assert all(order in all_orders for order in [sell_limit_1, sell_limit_2, sell_limit_3])
            inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
            assert len(inactive_orders) == 3
            assert stop_loss_2 in inactive_orders and all(order in inactive_orders for order in [sell_limit_2, sell_limit_3])
            # stop_loss_1 is reduced
            assert stop_loss_1.origin_quantity == decimal.Decimal("0.6")  # 0.8 - 0.2
            assert stop_loss_1.origin_price == decimal.Decimal(8)  # same price
            cancel_order_mock.reset_mock()
            edit_order_mock.reset_mock()

            # reverse step 1
            exchange_created_order = personal_data.StopLossOrder(trader_instance)
            exchange_created_order.update(
                order_type=enums.TraderOrderType.STOP_LOSS,
                symbol=DEFAULT_ORDER_SYMBOL,
                quantity=stop_loss_2.origin_quantity,
                price=stop_loss_2.origin_price,
                status=enums.OrderStatus.OPEN,
                exchange_order_id="recreated_stop_loss_2",
                fee={
                    enums.FeePropertyColumns.COST.value: 1,
                    enums.FeePropertyColumns.CURRENCY.value: "USDT",
                }
            )
            with mock.patch.object(order_factory, "create_order_instance_from_raw",
                              mock.Mock(return_value=exchange_created_order)) as create_order_instance_from_raw_mock, \
                 mock.patch.object(exchange_manager.exchange, "create_order",
                                   mock.AsyncMock(return_value=exchange_created_order)) as create_order_mock:
                await step_1_reverse(sell_limit_1, step_1_maybe_partially_inactive_orders)
                # stop loss 1 gets increased, stop loss 2 gets active again (re-created) and sell_limit_1 is back to inactive
                cancel_order_mock.assert_called_once()
                assert cancel_order_mock.mock_calls[0].args[0] == sell_limit_1.exchange_order_id
                edit_order_mock.assert_called_once()
                assert edit_order_mock.mock_calls[0].args[0] == stop_loss_1.exchange_order_id
                create_order_mock.assert_called_once()
                assert create_order_mock.mock_calls[0].kwargs["order_type"] == enums.TraderOrderType.STOP_LOSS
                create_order_instance_from_raw_mock.assert_called_once()
                assert stop_loss_2.is_cleared()
                assert stop_loss_1.origin_quantity == decimal.Decimal("0.8")
                assert stop_loss_1.origin_price == decimal.Decimal(8)  # same price
                assert exchange_created_order.origin_quantity == stop_loss_2.origin_quantity
                assert exchange_created_order.is_active is True
                updated_stop_loss_2[0] = exchange_created_order
                assert sell_limit_1.is_active is False
                all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
                assert len(all_orders) == 5
                assert all(order in all_orders for order in [stop_loss_1, updated_stop_loss_2[0]])
                assert len(tbtp_group.get_group_open_orders()) == 5
                assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)
                inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
                assert len(inactive_orders) == 3
                assert all(order in inactive_orders for order in [sell_limit_1, sell_limit_2, sell_limit_3])
                cancel_order_mock.reset_mock()
                edit_order_mock.reset_mock()
                create_order_mock.reset_mock()
                create_order_instance_from_raw_mock.reset_mock()

        async def step2_task():
            # STEP 2 => because of the group order locks, should be executed after step 1
            # sell_limit_2 become active: updated_stop_loss_2[0] (created in step 1) is cancelled, stop_loss_1 has no change
            step_2_maybe_partially_inactive_orders, step_2_reverse = await tbtp_group.adapt_before_order_becoming_active(sell_limit_2)
            sell_limit_2.is_active = True    # simulate now active order
            assert step_2_maybe_partially_inactive_orders == [updated_stop_loss_2[0]]
            cancel_order_mock.assert_called_once()
            edit_order_mock.assert_not_called()
            assert stop_loss_1.is_active is True
            assert updated_stop_loss_2[0].is_active is False
            assert sell_limit_1.is_active is False
            assert sell_limit_2.is_active is True
            assert sell_limit_3.is_active is False
            for order in [stop_loss_1, updated_stop_loss_2[0], sell_limit_1, sell_limit_2, sell_limit_3]:
                assert not order.is_cleared()
            # updated_stop_loss_2[0] is now inactive as well, sell limit could be updated to come active (done in strategy)
            all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
            assert len(all_orders) == 5
            assert len(tbtp_group.get_group_open_orders()) == 5
            assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)
            assert stop_loss_1 in all_orders and updated_stop_loss_2[0] in all_orders
            assert all(o in all_orders for o in [sell_limit_1, sell_limit_2, sell_limit_3])
            inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
            assert len(inactive_orders) == 3
            assert all(o in inactive_orders for o in [updated_stop_loss_2[0], sell_limit_1, sell_limit_3])
            # stop_loss_1 is NOT reduced
            assert stop_loss_1.origin_quantity == decimal.Decimal("0.8")
            cancel_order_mock.reset_mock()
            edit_order_mock.reset_mock()

            # reverse step 2
            exchange_created_order = personal_data.StopLossOrder(trader_instance)
            exchange_created_order.update(
                order_type=enums.TraderOrderType.STOP_LOSS,
                symbol=DEFAULT_ORDER_SYMBOL,
                quantity=stop_loss_2.origin_quantity,
                price=stop_loss_2.origin_price,
                status=enums.OrderStatus.OPEN,
                exchange_order_id="re-recreated_stop_loss_2",
                fee={
                    enums.FeePropertyColumns.COST.value: 1,
                    enums.FeePropertyColumns.CURRENCY.value: "USDT",
                }
            )
            with mock.patch.object(order_factory, "create_order_instance_from_raw",
                              mock.Mock(return_value=exchange_created_order)) as create_order_instance_from_raw_mock, \
                 mock.patch.object(exchange_manager.exchange, "create_order",
                                   mock.AsyncMock(return_value=exchange_created_order)) as create_order_mock:
                await step_2_reverse(sell_limit_2, step_2_maybe_partially_inactive_orders)
                # stop loss 1 does not change, stop loss 2 gets active again (re-created) and sell_limit_2 is back to inactive
                cancel_order_mock.assert_called_once()
                assert cancel_order_mock.mock_calls[0].args[0] == sell_limit_2.exchange_order_id
                edit_order_mock.assert_not_called()
                create_order_mock.assert_called_once()
                assert create_order_mock.mock_calls[0].kwargs["order_type"] == enums.TraderOrderType.STOP_LOSS
                create_order_instance_from_raw_mock.assert_called_once()
                assert updated_stop_loss_2[0].is_cleared()
                assert stop_loss_1.origin_quantity == decimal.Decimal("0.8")
                assert stop_loss_1.origin_price == decimal.Decimal(8)  # same price
                assert exchange_created_order.origin_quantity == updated_stop_loss_2[0].origin_quantity
                assert sell_limit_1.is_active is False
                assert exchange_created_order.is_active is True

                re_updated_stop_loss_2 = exchange_created_order
                assert sell_limit_1.is_active is False
                all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
                assert len(all_orders) == 5
                assert all(order in all_orders for order in [stop_loss_1, re_updated_stop_loss_2])
                assert len(tbtp_group.get_group_open_orders()) == 5
                assert all(order in tbtp_group.get_group_open_orders() for order in all_orders)

                inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
                assert len(inactive_orders) == 3
                assert all(order in inactive_orders for order in [sell_limit_1, sell_limit_2, sell_limit_3])
                cancel_order_mock.reset_mock()
                edit_order_mock.reset_mock()
                create_order_mock.reset_mock()
                create_order_instance_from_raw_mock.reset_mock()

        await asyncio.gather(
            step1_task(),
            step2_task(),
        )

def test_TrailingSideBalance_get_order_update(trailing_side_balance, order_f):
    order = order_f
    # no trailing profile
    assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
        personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
        personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
        personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: None,
        personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
        personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
    }

    # incompatible trailing profile
    order.trailing_profile = mock.Mock()
    assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
        personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
        personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
        personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: None,
        personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
        personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
    }

    order.trailing_profile = personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    # filled price does not trigger trailing: trailing trigger price is not reached
    closed_order = personal_data.Order(order.trader)
    closed_order.origin_price = decimal.Decimal(9000)
    trailing_side_balance.closed_order = closed_order
    with mock.patch.object(
        order_util, "get_potentially_outdated_price", mock.Mock(return_value=(decimal.Decimal(8900), True))
    ) as get_potentially_outdated_price_mock:
        assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
            personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: None,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
        }
        get_potentially_outdated_price_mock.assert_called_once()

    # filled price triggers trailing: trailing trigger price is reached by closed order even though current price is bellow
    closed_order = personal_data.Order(order.trader)
    closed_order.origin_price = decimal.Decimal(10000)
    trailing_side_balance.closed_order = closed_order
    with mock.patch.object(
        order_util, "get_potentially_outdated_price", mock.Mock(return_value=(decimal.Decimal(8900), True))
    ) as get_potentially_outdated_price_mock:
        assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
            personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: decimal.Decimal(10000),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
        }
        get_potentially_outdated_price_mock.assert_called_once()

    # filled price does not trailing: trailing trigger price is reached by current price even though closed order is bellow
    # BUT trailing threshold has already been reached (trailed already)
    closed_order = personal_data.Order(order.trader)
    closed_order.origin_price = decimal.Decimal(1000)
    trailing_side_balance.closed_order = closed_order
    with mock.patch.object(
        order_util, "get_potentially_outdated_price", mock.Mock(return_value=(decimal.Decimal(10000), True))
    ) as get_potentially_outdated_price_mock:
        assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
            personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: None,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
        }
        get_potentially_outdated_price_mock.assert_called_once()

    # filled price triggers trailing: trailing trigger price is reached by current price even though closed order is bellow
    closed_order = personal_data.Order(order.trader)
    closed_order.origin_price = decimal.Decimal(1000)
    trailing_side_balance.closed_order = closed_order
    with mock.patch.object(
        order_util, "get_potentially_outdated_price", mock.Mock(return_value=(decimal.Decimal(12000), True))
    ) as get_potentially_outdated_price_mock:
        assert trailing_side_balance.get_order_update(order, decimal.Decimal(12)) == {
            personal_data.TrailingOnFilledTPBalancedOrderGroup.ORDER: order,
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_QUANTITY: decimal.Decimal(12),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE: decimal.Decimal(12000),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_QUANTITY: decimal.Decimal(0),
            personal_data.TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE: decimal.Decimal(0),
        }
        get_potentially_outdated_price_mock.assert_called_once()
