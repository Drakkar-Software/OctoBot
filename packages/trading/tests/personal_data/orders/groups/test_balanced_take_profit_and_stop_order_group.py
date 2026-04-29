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
import octobot_trading.personal_data.orders.groups.balanced_take_profit_and_stop_order_group as \
    balanced_take_profit_and_stop_order_group
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_util as order_util
from tests.exchanges import backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests.personal_data.orders.groups import order_mock
from tests.personal_data import DEFAULT_ORDER_SYMBOL
from tests.personal_data.orders import created_order
from tests.exchanges import simulated_trader, simulated_exchange_manager


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def btps_group(backtesting_exchange_manager):
    orders_manager = mock.Mock()
    orders_manager.get_order_from_group = mock.Mock()
    return personal_data.BalancedTakeProfitAndStopOrderGroup("name",  orders_manager)


@pytest.fixture
def side_balance():
    return balanced_take_profit_and_stop_order_group.SideBalance(None, False)


async def test_on_fill(btps_group):
    order = order_mock()
    # mock btps_group.orders_manager instead of btps_group._balance_orders to allow cythonized class tests
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
            as get_order_from_group_mock:
        await btps_group.on_fill(order)
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()

        await btps_group.on_fill(order, ["hi", "ho"])
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()


async def test_on_cancel(btps_group):
    order = order_mock()
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
            as get_order_from_group_mock:
        await btps_group.on_cancel(order)
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()

        await btps_group.on_cancel(order, ["hi", "ho"])
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()


async def test_enable(btps_group):
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
            as get_order_from_group_mock:
        await btps_group.enable(False)
        get_order_from_group_mock.assert_not_called()
        await btps_group.enable(True)
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        await btps_group.enable(True)
        get_order_from_group_mock.assert_called_once()


async def test_can_create_order(btps_group):
    order_1 = order_mock(origin_quantity=decimal.Decimal(1), order_type=enums.TraderOrderType.SELL_LIMIT,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    order_2 = order_mock(origin_quantity=decimal.Decimal(5), order_type=enums.TraderOrderType.BUY_MARKET,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    order_3 = order_mock(origin_quantity=decimal.Decimal(10), order_type=enums.TraderOrderType.TRAILING_STOP,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                           mock.Mock(return_value=[])) as get_order_from_group_mock:
        # 0 size order
        assert btps_group.can_create_order(enums.TraderOrderType.STOP_LOSS, decimal.Decimal(0)) is True
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        # no order, no imbalance
        assert btps_group.can_create_order(enums.TraderOrderType.STOP_LOSS, decimal.Decimal(1)) is False
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                           mock.Mock(return_value=[order_1, order_2, order_3])) as get_order_from_group_mock:
        # enough imbalance
        assert btps_group.can_create_order(enums.TraderOrderType.SELL_LIMIT, decimal.Decimal(1)) is True
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        assert btps_group.can_create_order(enums.TraderOrderType.SELL_LIMIT, decimal.Decimal(4)) is True
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()

        # not enough
        assert btps_group.can_create_order(enums.TraderOrderType.SELL_LIMIT, decimal.Decimal("4.000001")) is False
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        assert btps_group.can_create_order(enums.TraderOrderType.STOP_LOSS, decimal.Decimal("0.00001")) is False
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()


async def test_get_max_order_quantity(btps_group):
    order_1 = order_mock(origin_quantity=decimal.Decimal(1), order_type=enums.TraderOrderType.SELL_LIMIT,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    order_2 = order_mock(origin_quantity=decimal.Decimal(5), order_type=enums.TraderOrderType.BUY_MARKET,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    order_3 = order_mock(origin_quantity=decimal.Decimal(10), order_type=enums.TraderOrderType.TRAILING_STOP,
                         origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                           mock.Mock(return_value=[])) as get_order_from_group_mock:
        # no order, no imbalance
        assert btps_group.get_max_order_quantity(enums.TraderOrderType.STOP_LOSS) == constants.ZERO
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                           mock.Mock(return_value=[order_1, order_2, order_3])) as get_order_from_group_mock:
        # imbalance
        assert btps_group.get_max_order_quantity(enums.TraderOrderType.SELL_LIMIT) == decimal.Decimal(4)
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        assert btps_group.get_max_order_quantity(enums.TraderOrderType.STOP_LOSS) == constants.ZERO
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()


async def test_balance_orders(btps_group):
    order_1 = order_mock(origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(10),
                         order_type=enums.TraderOrderType.SELL_LIMIT, origin_quantity=decimal.Decimal("1.5"))
    order_2 = order_mock(origin_price=decimal.Decimal(5), created_last_price=decimal.Decimal(3),
                         order_type=enums.TraderOrderType.SELL_LIMIT, origin_quantity=decimal.Decimal("11"))
    order_3 = order_mock(origin_price=decimal.Decimal(10), created_last_price=decimal.Decimal(11),
                         order_type=enums.TraderOrderType.STOP_LOSS, origin_quantity=decimal.Decimal("10"))
    order_4 = order_mock(origin_price=decimal.Decimal(42), created_last_price=decimal.Decimal(2),
                         order_type=enums.TraderOrderType.STOP_LOSS, origin_quantity=decimal.Decimal("20"))
    with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                           mock.Mock(return_value=[order_1, order_2, order_3, order_4])) as get_order_from_group_mock:
        base_balancing_order = ["existing_order"]
        btps_group.balancing_orders = base_balancing_order
        # 1. not enabled
        btps_group.enabled = False
        await btps_group._balance_orders(order_1, ["ignored_orders"], False)
        get_order_from_group_mock.assert_not_called()
        assert btps_group.balancing_orders == ["existing_order"]
        assert btps_group.balancing_orders is base_balancing_order

        # 2. enabled
        btps_group.enabled = True
        await btps_group._balance_orders(order_4, ["ignored_orders"], True)
        get_order_from_group_mock.assert_called_once()
        get_order_from_group_mock.reset_mock()
        order_1.trader.edit_order.assert_not_called()
        order_1.trader.cancel_order.assert_called_once_with(
            order_1, ignored_order=order_4, wait_for_cancelling=True,
            cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
            force_if_disabled=False
        )
        order_2.trader.edit_order.assert_called_once_with(
            order_2,
            edited_quantity=decimal.Decimal(10),
            edited_price=None,
            edited_stop_price=None,
            edited_current_price=None,
            params=None
        )
        order_2.trader.cancel_order.assert_not_called()
        order_3.trader.edit_order.assert_not_called()
        order_3.trader.cancel_order.assert_not_called()
        order_4.trader.edit_order.assert_not_called()
        order_4.trader.cancel_order.assert_not_called()
        assert btps_group.balancing_orders == ["existing_order"]
        assert btps_group.balancing_orders is not base_balancing_order  # changed list during orders registration

        def _get_order_update(order, updated_quantity):
            return {
                balanced_take_profit_and_stop_order_group.BalancedTakeProfitAndStopOrderGroup.ORDER: order,
                balanced_take_profit_and_stop_order_group.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: updated_quantity,
                balanced_take_profit_and_stop_order_group.BalancedTakeProfitAndStopOrderGroup.UPDATED_PRICE: decimal.Decimal(111),
            }
        for order in (order_1, order_2, order_3, order_4):
            order.trader.edit_order.reset_mock()
            order.trader.cancel_order.reset_mock()
        # 3. with updated price
        with mock.patch.object(
            balanced_take_profit_and_stop_order_group.SideBalance, "get_order_update",
            mock.Mock(side_effect=_get_order_update)
        ) as get_order_update:
            btps_group.enabled = True
            await btps_group._balance_orders(order_4, ["ignored_orders"], True)
            get_order_from_group_mock.assert_called_once()
            get_order_from_group_mock.reset_mock()
            order_1.trader.edit_order.assert_not_called()
            order_1.trader.cancel_order.assert_called_once_with(
                order_1, ignored_order=order_4, wait_for_cancelling=True,
                cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
                force_if_disabled=False
            )
            order_2.trader.edit_order.assert_called_once_with(
                order_2,
                edited_quantity=decimal.Decimal(10),
                edited_price=decimal.Decimal(111),
                edited_stop_price=None,
                edited_current_price=None,
                params=None
            )
            order_2.trader.cancel_order.assert_not_called()
            order_3.trader.edit_order.assert_called_once_with(
                order_3,
                edited_quantity=None,
                edited_price=decimal.Decimal(111),
                edited_stop_price=None,
                edited_current_price=None,
                params=None
            )
            order_3.trader.cancel_order.assert_not_called()
            order_4.trader.edit_order.assert_not_called()
            order_4.trader.cancel_order.assert_not_called()
            assert btps_group.balancing_orders == ["existing_order"]
            assert btps_group.balancing_orders is not base_balancing_order  # changed list during orders registration


async def test_get_balance(btps_group):
    order_1 = order_mock(order_type="order_type", origin_price=decimal.Decimal(1),
                         created_last_price=decimal.Decimal(2))
    order_2 = order_mock(order_type="order_type", origin_price=decimal.Decimal(1),
                         created_last_price=decimal.Decimal(2))
    with mock.patch.object(order_util, "is_stop_order", mock.Mock(return_value=False)) as is_stop_order_mock:
        with mock.patch.object(btps_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[])) \
             as get_order_from_group_mock:
            balance = btps_group._get_balance(order_1, None, True)
            assert balance[btps_group.TAKE_PROFIT].orders == []
            assert balance[btps_group.STOP].orders == []
            get_order_from_group_mock.assert_called_once()
            is_stop_order_mock.assert_not_called()

        with mock.patch.object(btps_group.orders_manager, "get_order_from_group", mock.Mock(return_value=[order_1, order_2])) \
             as get_order_from_group_mock:
            balance = btps_group._get_balance(order_1, None, True)
            assert balance[btps_group.TAKE_PROFIT].orders == [order_2]
            assert balance[btps_group.STOP].orders == []
            get_order_from_group_mock.assert_called_once()
            is_stop_order_mock.assert_called_once_with("order_type")
            is_stop_order_mock.reset_mock()

        with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                               mock.Mock(return_value=[order_1, order_2])) as get_order_from_group_mock:
            balance = btps_group._get_balance(order_1, [order_2], False)
            assert balance[btps_group.TAKE_PROFIT].orders == []
            assert balance[btps_group.STOP].orders == []
            get_order_from_group_mock.assert_called_once()
            is_stop_order_mock.assert_not_called()

    with mock.patch.object(order_util, "is_stop_order", mock.Mock(return_value=True)) as is_stop_order_mock:
        with mock.patch.object(btps_group.orders_manager, "get_order_from_group",
                               mock.Mock(return_value=[order_1, order_2])) as get_order_from_group_mock:
            balance = btps_group._get_balance(order_1, None, False)
            assert balance[btps_group.TAKE_PROFIT].orders == []
            assert balance[btps_group.STOP].orders == [order_2]
            get_order_from_group_mock.assert_called_once()
            is_stop_order_mock.assert_called_once_with("order_type")
            is_stop_order_mock.reset_mock()


async def test_balanced_adapt_before_order_becoming_active_and_reverse_swap(simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    trader_instance.allow_artificial_orders = False
    trader_instance.enable_inactive_orders = True
    trader_instance.simulate = False
    exchange_manager.is_backtesting = True  # force update_order_status
    btp_group = personal_data.BalancedTakeProfitAndStopOrderGroup(
        "name", exchange_manager.exchange_personal_data.orders_manager
    )
    assert isinstance(btp_group.active_order_swap_strategy, personal_data.StopFirstActiveOrderSwapStrategy)
    stop_loss_1 = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss_1.update(
        price=decimal.Decimal(8),
        quantity=decimal.Decimal("0.8"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=btp_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss_1, decimal.Decimal(8), False),
    )
    stop_loss_2 = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                              trader_instance, side=enums.TradeOrderSide.SELL)
    stop_loss_2.update(
        price=decimal.Decimal(10),
        quantity=decimal.Decimal("0.2"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.STOP_LOSS,
        group=btp_group,
        is_active=True,
        active_trigger=personal_data.create_order_price_trigger(stop_loss_2, decimal.Decimal(10), False),
    )
    sell_limit_1 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_1.update(
        price=decimal.Decimal(20),
        quantity=decimal.Decimal("0.4"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=btp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_1, decimal.Decimal(20), True),
    )
    sell_limit_2 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_2.update(
        price=decimal.Decimal(30),
        quantity=decimal.Decimal("0.25"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=btp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_2, decimal.Decimal(30), True),
    )
    sell_limit_3 = created_order(personal_data.SellLimitOrder, enums.TraderOrderType.SELL_LIMIT,
                               trader_instance, side=enums.TradeOrderSide.SELL)
    sell_limit_3.update(
        price=decimal.Decimal(40),
        quantity=decimal.Decimal("0.35"),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.SELL_LIMIT,
        group=btp_group,
        is_active=False,
        active_trigger=personal_data.create_order_price_trigger(sell_limit_3, decimal.Decimal(40), True),
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
    async def _edit_order(*args, quantity=None, price=None, **kwargs):
        edited_stop_loss = created_order(personal_data.StopLossLimitOrder, enums.TraderOrderType.STOP_LOSS,
                                        trader_instance, side=enums.TradeOrderSide.SELL)
        edited_stop_loss.update(
            price=price or decimal.Decimal(10),
            quantity=quantity,
            symbol=DEFAULT_ORDER_SYMBOL,
            order_type=enums.TraderOrderType.STOP_LOSS,
            group=btp_group,
            is_active=True,
            active_trigger=personal_data.create_order_price_trigger(edited_stop_loss, decimal.Decimal(10), False),
        )
        order_dict = edited_stop_loss.to_dict()
        order_dict.pop(enums.ExchangeConstantsOrderColumns.ID.value)
        return order_dict


    with mock.patch.object(exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock, \
            mock.patch.object(exchange_manager.exchange, "edit_order",
                              mock.AsyncMock(side_effect=_edit_order)) as edit_order_mock:
        # sell_limit_1 become active: stop_loss_2 is now inactive, stop_loss_1 is reduced and remains active
        now_maybe_partially_inactive_orders, _ = await btp_group.adapt_before_order_becoming_active(sell_limit_1)
        sell_limit_1.is_active=True    # simulate now active order
        assert now_maybe_partially_inactive_orders == [stop_loss_2, stop_loss_1]
        cancel_order_mock.assert_called_once()
        edit_order_mock.assert_called_once()
        assert stop_loss_1.is_active is True
        assert stop_loss_2.is_active is False
        for order in [stop_loss_1, stop_loss_2, sell_limit_1, sell_limit_2, sell_limit_3]:
            assert not order.is_cleared()
        # stop_loss_2 is now inactive as well, sell limit could be updated to come active (done in strategy)
        all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert len(all_orders) == 5
        assert stop_loss_1 in all_orders and stop_loss_2 in all_orders
        assert all(order in all_orders for order in [sell_limit_1, sell_limit_2, sell_limit_3])
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert len(inactive_orders) == 3
        assert stop_loss_2 in inactive_orders and all(order in inactive_orders for order in [sell_limit_2, sell_limit_3])
        # stop_loss_1 is reduced
        assert stop_loss_1.origin_quantity == decimal.Decimal("0.6")  # 0.8 - 0.2
        cancel_order_mock.reset_mock()
        edit_order_mock.reset_mock()

        # fill sell_limit_1: stop_loss_2 gets canceled
        await sell_limit_1.on_fill(force_fill=True)
        # stop_loss_2 is canceled
        assert sell_limit_1.is_closed()
        assert stop_loss_2.is_closed()
        assert sell_limit_1.is_cleared()
        assert stop_loss_2.is_cleared()
        all_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders()
        assert len(all_orders) == 3
        assert stop_loss_1 in all_orders and stop_loss_2 not in all_orders
        assert all(order in all_orders for order in [sell_limit_2, sell_limit_3])
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert len(inactive_orders) == 2
        assert all(order in inactive_orders for order in [sell_limit_2, sell_limit_3])
        assert stop_loss_1.is_active is True
        assert sell_limit_2.is_active is False
        assert sell_limit_3.is_active is False

        # sell_limit_2 become active: stop_loss_1 is reduced and remains active
        # stop_loss_1 is reduced again, no order is canceled
        now_maybe_partially_inactive_orders, reverse_swap = await btp_group.adapt_before_order_becoming_active(sell_limit_2)
        sell_limit_2.is_active=True    # simulate now active order
        assert now_maybe_partially_inactive_orders == [stop_loss_1]
        cancel_order_mock.assert_not_called()
        edit_order_mock.assert_called_once()
        assert stop_loss_1.is_active is True
        assert sell_limit_2.is_active is True
        assert sell_limit_3.is_active is False
        for order in [stop_loss_1, sell_limit_2, sell_limit_3]:
            assert not order.is_cleared()
        # stop_loss_2 is now inactive as well, could be to update sell limit to come active (done in strategy)
        inactive_orders = order.exchange_manager.exchange_personal_data.orders_manager.get_all_orders(active=False)
        assert inactive_orders == [sell_limit_3]
        # stop_loss_1 is reduced
        assert stop_loss_1.origin_quantity == decimal.Decimal("0.35")  # 0.8 - 0.2 - 0.25
        cancel_order_mock.reset_mock()
        edit_order_mock.reset_mock()

        # now reverse swap
        with mock.patch.object(btp_group, "adapt_before_order_becoming_active", mock.AsyncMock()) as adapt_before_order_becoming_active_mock, \
            mock.patch.object(order_util, "create_as_active_order_on_exchange", mock.AsyncMock()) as create_as_active_order_on_exchange_mock, \
            mock.patch.object(btp_group, "_apply_update_order_actions", mock.AsyncMock()) as _apply_update_order_actions_mock, \
            mock.patch.object(order_util, "update_order_as_inactive_on_exchange", mock.AsyncMock()) as update_order_as_inactive_on_exchange_mock:
            await reverse_swap("order_0", ["order_1", "order_2"])
            update_order_as_inactive_on_exchange_mock.assert_called_once_with("order_0", False)
            adapt_before_order_becoming_active_mock.assert_not_called()
            create_as_active_order_on_exchange_mock.assert_not_called()   # no order to re-create (no cancelled order in previous step)
            _apply_update_order_actions_mock.assert_called_once()
            reverse_actions = _apply_update_order_actions_mock.mock_calls[0].args[0]
            assert len(reverse_actions) == 1
            assert reverse_actions[0][btp_group.ORDER] is stop_loss_1
            assert reverse_actions[0][btp_group.UPDATED_QUANTITY] == decimal.Decimal("0.60")

        # without deactivated orders
        await reverse_swap(sell_limit_2, [])
        # stop loss gets increased again and sell_limit_2 is back to inactive
        cancel_order_mock.assert_called_once()
        edit_order_mock.assert_called_once()
        assert stop_loss_1.is_active is True
        assert stop_loss_1.origin_quantity == decimal.Decimal("0.6")  # 0.8 - 0.2
        assert sell_limit_2.is_active is False


async def test_SideBalance_add_order(side_balance):
    assert side_balance.orders == []
    order_1 = order_mock(origin_price=decimal.Decimal(1), created_last_price=decimal.Decimal(2))
    order_2 = order_mock(origin_price=decimal.Decimal(15), created_last_price=decimal.Decimal(3))
    order_3 = order_mock(origin_price=decimal.Decimal(50), created_last_price=decimal.Decimal(55))
    side_balance.add_order(order_1)
    assert side_balance.orders == [order_1]
    side_balance.add_order(order_2)
    assert side_balance.orders == [order_2, order_1]
    side_balance.add_order(order_3)
    assert side_balance.orders == [order_2, order_3, order_1]


async def test_SideBalance_get_actions_to_balance_special_inputs(side_balance):
    with mock.patch.object(side_balance, "get_balance", mock.Mock(return_value=decimal.Decimal("-1"))):
        # target balance can't be negative (order quantity is always positive). value treated as abs()
        assert side_balance.get_actions_to_balance(constants.ONE) == {
            personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
        }
    with mock.patch.object(side_balance, "get_balance", mock.Mock(return_value=constants.ONE)):
        # target balance == balance: nothing to do
        assert side_balance.get_actions_to_balance(constants.ONE) == {
            personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
        }
    with mock.patch.object(side_balance, "get_balance", mock.Mock(return_value=constants.ONE)):
        # target balance > balance: nothing to do (can't create order to increase)
        assert side_balance.get_actions_to_balance(decimal.Decimal("0.6")) == {
            personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
        }
    with mock.patch.object(side_balance, "get_balance", mock.Mock(return_value=constants.ONE)):
        # no order to create actions
        assert side_balance.get_actions_to_balance(decimal.Decimal("10")) == {
            personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
        }


async def test_SideBalance_get_actions_to_balance_normal_inputs(side_balance):
    order_0_1 = order_mock(origin_quantity=decimal.Decimal("2.899999"))
    order_0_2 = order_mock(origin_quantity=decimal.Decimal("0.111111"))
    order_0_3 = order_mock(origin_quantity=decimal.Decimal("3.15545145441"))
    side_balance.orders = [order_0_1, order_0_2, order_0_3]
    assert side_balance.get_actions_to_balance(decimal.Decimal("3.15545145441")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_0_1, order_0_2],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_0_3,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: None,
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal('3.15545145441')
        }],
    }
    order_1 = order_mock(origin_quantity=decimal.Decimal("1"))
    order_2 = order_mock(origin_quantity=decimal.Decimal("6.42"))
    side_balance.orders = [order_2]
    assert side_balance.get_actions_to_balance(decimal.Decimal("3")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_2,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: decimal.Decimal("3"),
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("6.42")
        }],
    }
    side_balance.orders = [order_1, order_2]
    assert side_balance.get_actions_to_balance(decimal.Decimal("3")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_1],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_2,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: decimal.Decimal("3"),
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("6.42")
        }],
    }
    order_2 = order_mock(origin_quantity=decimal.Decimal("6.42"))
    order_3 = order_mock(origin_quantity=decimal.Decimal("11.888998327557457"))
    side_balance.orders = [order_1, order_2, order_3]
    assert side_balance.get_actions_to_balance(decimal.Decimal("3")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_1, order_2],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_3,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: decimal.Decimal("3"),
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("11.888998327557457")
        }],
    }
    order_4 = order_mock(origin_quantity=decimal.Decimal("0.1"))
    side_balance.orders = [order_1, order_2, order_3, order_4]
    # keep order_4 untouched as it is the closest from price and can be included in target balance
    assert side_balance.get_actions_to_balance(decimal.Decimal("3")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_1, order_2],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_3,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: decimal.Decimal("2.9"),
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("11.888998327557457")
        },{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_4,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: None,
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("0.1")
        }],
    }
    side_balance.orders = [order_1, order_4, order_2, order_3]
    assert side_balance.get_actions_to_balance(decimal.Decimal("3")) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_1, order_4, order_2],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [{
            personal_data.BalancedTakeProfitAndStopOrderGroup.ORDER: order_3,
            personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: decimal.Decimal("3"),
            personal_data.BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: decimal.Decimal("11.888998327557457")
        }],
    }

    side_balance.orders = [order_1, order_4, order_2, order_3]
    assert side_balance.get_actions_to_balance(constants.ZERO) == {
        personal_data.BalancedTakeProfitAndStopOrderGroup.CANCEL: [order_1, order_4, order_2, order_3],
        personal_data.BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
    }


async def test_SideBalance_get_balance(side_balance):
    assert side_balance.get_balance() is constants.ZERO
    order_1 = order_mock(origin_quantity=decimal.Decimal(1))
    order_2 = order_mock(origin_quantity=decimal.Decimal(10))
    order_mock(origin_quantity=decimal.Decimal(50))
    side_balance.orders = [order_1, order_2]
    assert side_balance.get_balance() == decimal.Decimal(11)
