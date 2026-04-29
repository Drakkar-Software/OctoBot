#  Drakkar-Software OctoBot-Tentacles
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

import pytest
import mock
import decimal
import os

import tentacles.Meta.Keywords.scripting_library.orders.order_types.create_order as create_order
import tentacles.Meta.Keywords.scripting_library.orders.position_size as position_size
import tentacles.Meta.Keywords.scripting_library.orders.grouping as grouping
import octobot_trading.enums as trading_enums
import octobot_trading.errors as errors
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.modes.script_keywords as script_keywords

from tentacles.Meta.Keywords.scripting_library.tests import event_loop, null_context, mock_context, symbol_market, \
    skip_if_octobot_trading_mocking_disabled
from tentacles.Meta.Keywords.scripting_library.tests.exchanges import backtesting_trader, backtesting_config, \
    backtesting_exchange_manager, fake_backtesting


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_order_instance(mock_context):
    with mock.patch.object(create_order, "_get_order_quantity_and_side",
                           mock.AsyncMock(return_value=(decimal.Decimal(1), "sell"))) \
            as _get_order_quantity_and_side_mock, \
            mock.patch.object(create_order, "_get_order_details",
                              mock.AsyncMock(return_value=(1, 2, 3, 4, 5, 6, 7, 8, 9))) \
            as _get_order_details_mock, \
            mock.patch.object(script_keywords, "get_price_with_offset", mock.AsyncMock(return_value=42)) as get_offset_mock, \
            mock.patch.object(create_order, "_create_order", mock.AsyncMock()) as _create_order_mock:
        with mock.patch.object(create_order, "_paired_order_is_closed", mock.Mock(return_value=True)) \
             as _paired_order_is_closed_mock:
            order = mock.Mock(is_open=mock.Mock(return_value=False))
            assert [] == await create_order.create_order_instance(
                mock_context, "side", "symbol", "order_amount", "order_target_position",
                "stop_loss_offset", "stop_loss_tag", "stop_loss_type", "stop_loss_group",
                "take_profit_offset", "take_profit_tag", "take_profit_type", "take_profit_group",
                "order_type_name", "order_offset", "order_min_offset", "order_max_offset", "order_limit_offset",
                "slippage_limit", "time_limit", "reduce_only", "post_only", "tag", "group", [order])
            _paired_order_is_closed_mock.assert_called_once_with(mock_context, "group")
            _get_order_quantity_and_side_mock.assert_not_called()
            _get_order_details_mock.assert_not_called()
            get_offset_mock.assert_not_called()
            _create_order_mock.assert_not_called()
        with mock.patch.object(create_order, "_paired_order_is_closed", mock.Mock(return_value=False)) \
             as _paired_order_is_closed_mock:
            order = mock.Mock(is_open=mock.Mock(return_value=False))
            await create_order.create_order_instance(
                mock_context, "side", "symbol", "order_amount", "order_target_position",
                "stop_loss_offset", "stop_loss_tag", "stop_loss_type", "stop_loss_group",
                "take_profit_offset", "take_profit_tag", "take_profit_type", "take_profit_group",
                "order_type_name", "order_offset", "order_min_offset", "order_max_offset", "order_limit_offset",
                "slippage_limit", "time_limit", "reduce_only", "post_only", "tag", "group", [order])
            _paired_order_is_closed_mock.assert_called_once_with(mock_context, "group")
            _get_order_quantity_and_side_mock.assert_called_once_with(mock_context, "order_amount",
                                                                      "order_target_position", "order_type_name",
                                                                      "side", "reduce_only", False)
            _get_order_details_mock.assert_called_once_with(mock_context, "order_type_name", "sell", "order_offset",
                                                            "reduce_only", "order_limit_offset")
            assert get_offset_mock.call_count == 2
            _create_order_mock.assert_called_once_with(
                context=mock_context, symbol="symbol", order_quantity=decimal.Decimal(1), order_price=2, tag="tag",
                order_type_name="order_type_name", input_side="side",
                side="sell", final_side=3, order_type=1, order_min_offset="order_min_offset", max_offset_val=7,
                reduce_only=4, group="group",
                stop_loss_price=42, stop_loss_tag="stop_loss_tag", stop_loss_type="stop_loss_type",
                stop_loss_group="stop_loss_group",
                take_profit_price=42, take_profit_tag="take_profit_tag", take_profit_type="take_profit_type",
                take_profit_group="take_profit_group",
                wait_for=[order],
                truncate=False,
                order_amount='order_amount', order_target_position='order_target_position')


async def test_paired_order_is_closed(mock_context, skip_if_octobot_trading_mocking_disabled):
    # skip_if_octobot_trading_mocking_disabled oco_group, "get_group_open_orders"
    assert create_order._paired_order_is_closed(mock_context, None) is False
    oco_group = grouping.create_one_cancels_the_other_group(mock_context)
    assert create_order._paired_order_is_closed(mock_context, oco_group) is False
    order = mock.Mock()
    order_2 = mock.Mock()
    order_2.is_closed = mock.Mock(return_value=True)
    if os.getenv('CYTHON_IGNORE'):
        return
    with mock.patch.object(oco_group, "get_group_open_orders", mock.Mock(return_value=[order, order_2])) as \
        get_group_open_orders_mock:
        with mock.patch.object(order, "is_closed", mock.Mock(return_value=True)) as is_closed_mock:
            assert create_order._paired_order_is_closed(mock_context, oco_group) is True
            is_closed_mock.assert_called_once()
            get_group_open_orders_mock.assert_called_once()
            get_group_open_orders_mock.reset_mock()
        with mock.patch.object(order, "is_closed", mock.Mock(return_value=False)) as is_closed_mock:
            assert create_order._paired_order_is_closed(mock_context, oco_group) is False
            is_closed_mock.assert_called_once()
            get_group_open_orders_mock.assert_called_once()
    order.order_group = None
    null_context.just_created_orders = [order]
    with mock.patch.object(order, "is_closed", mock.Mock(return_value=True)) as is_closed_mock:
        assert create_order._paired_order_is_closed(null_context, oco_group) is False
        is_closed_mock.assert_not_called()
        order.order_group = oco_group
        assert create_order._paired_order_is_closed(null_context, oco_group) is True
        is_closed_mock.assert_called_once()
        order.order_group = mock.Mock()
        is_closed_mock.reset_mock()
        assert create_order._paired_order_is_closed(null_context, oco_group) is False
        is_closed_mock.assert_not_called()


async def test_use_total_holding():
    with mock.patch.object(create_order, "_is_stop_order", mock.Mock(return_value=False)) as _is_stop_order_mock:
        assert create_order._use_total_holding("type") is False
        _is_stop_order_mock.assert_called_once_with("type")
    with mock.patch.object(create_order, "_is_stop_order", mock.Mock(return_value=True)) as _is_stop_order_mock:
        assert create_order._use_total_holding("type2") is True
        _is_stop_order_mock.assert_called_once_with("type2")


async def test_is_stop_order():
    assert create_order._is_stop_order("") is False
    assert create_order._is_stop_order("market") is False
    assert create_order._is_stop_order("limit") is False
    assert create_order._is_stop_order("stop_loss") is True
    assert create_order._is_stop_order("stop_market") is True
    assert create_order._is_stop_order("stop_limit") is True
    assert create_order._is_stop_order("trailing_stop_loss") is True
    assert create_order._is_stop_order("trailing_market") is False
    assert create_order._is_stop_order("trailing_limit") is False


async def test_get_order_quantity_and_side(null_context):
    # order_amount and order_target_position are both not set
    with pytest.raises(errors.InvalidArgumentError):
        await create_order._get_order_quantity_and_side(null_context, None, None, "", "", True, False)

    # order_amount and order_target_position are set
    with pytest.raises(errors.InvalidArgumentError):
        await create_order._get_order_quantity_and_side(null_context, 1, 2, "", "", True, False)

    # order_amount but no side
    with pytest.raises(errors.InvalidArgumentError):
        await create_order._get_order_quantity_and_side(null_context, 1, None, "", None, True, False)
    with pytest.raises(errors.InvalidArgumentError):
        await create_order._get_order_quantity_and_side(null_context, 1, None, "", "fsdsfds", True, True), False

    with mock.patch.object(position_size, "get_amount",
                           mock.AsyncMock(return_value=decimal.Decimal(1))) as get_amount_mock:
        with mock.patch.object(create_order, "_use_total_holding",
                               mock.Mock(return_value=False)) as _use_total_holding_mock, \
                mock.patch.object(create_order, "_is_stop_order",
                                  mock.Mock(return_value=False)) as _is_stop_order_mock:
            assert await create_order._get_order_quantity_and_side(null_context, 1, None, "", "sell", True, False) \
                   == (decimal.Decimal(1), "sell")
            get_amount_mock.assert_called_once_with(null_context, 1, "sell", True, False, use_total_holding=False,
                                                    unknown_portfolio_on_creation=False)
            get_amount_mock.reset_mock()
            _is_stop_order_mock.assert_called_once_with("")
            _use_total_holding_mock.assert_called_once_with("")
        with mock.patch.object(create_order, "_use_total_holding",
                               mock.Mock(return_value=True)) as _use_total_holding_mock, \
                mock.patch.object(create_order, "_is_stop_order",
                                 mock.Mock(return_value=True)) as _is_stop_order_mock:
            assert await create_order._get_order_quantity_and_side(null_context, 1, None, "order_type", "sell", False,
                                                                   True) \
                   == (decimal.Decimal(1), "sell")
            get_amount_mock.assert_called_once_with(null_context, 1, "sell", False, True, use_total_holding=True,
                                                    unknown_portfolio_on_creation=True)
            get_amount_mock.reset_mock()
            _is_stop_order_mock.assert_called_once_with("order_type")
            _use_total_holding_mock.assert_called_once_with("order_type")

    with mock.patch.object(position_size, "get_target_position",
                           mock.AsyncMock(return_value=(decimal.Decimal(10), "buy"))) as get_target_position_mock:
        with mock.patch.object(create_order, "_use_total_holding",
                               mock.Mock(return_value=True)) as _use_total_holding_mock, \
             mock.patch.object(create_order, "_is_stop_order",
                               mock.Mock(return_value=False)) as _is_stop_order_mock:
            assert await create_order._get_order_quantity_and_side(null_context, None, 1, "order_type", None, True,
                                                                   False) \
                   == (decimal.Decimal(10), "buy")
            get_target_position_mock.assert_called_once_with(null_context, 1, True, False, use_total_holding=True,
                                                             unknown_portfolio_on_creation=False)
            get_target_position_mock.reset_mock()
            _is_stop_order_mock.assert_called_once_with("order_type")
            _use_total_holding_mock.assert_called_once_with("order_type")
        with mock.patch.object(create_order, "_use_total_holding",
                               mock.Mock(return_value=False)) as _use_total_holding_mock, \
             mock.patch.object(create_order, "_is_stop_order",
                               mock.Mock(return_value=True)) as _is_stop_order_mock:
            assert await create_order._get_order_quantity_and_side(null_context, None, 1, "order_type", None, False,
                                                                   True) \
                   == (decimal.Decimal(10), "buy")
            get_target_position_mock.assert_called_once_with(null_context, 1, False, True, use_total_holding=False,
                                                             unknown_portfolio_on_creation=True)
            get_target_position_mock.reset_mock()
            _is_stop_order_mock.assert_called_once_with("order_type")
            _use_total_holding_mock.assert_called_once_with("order_type")


async def test_get_order_details(null_context):
    ten = decimal.Decimal(10)
    with mock.patch.object(script_keywords, "get_price_with_offset", mock.AsyncMock(return_value=ten)) as get_offset_mock:

        async def _test_market(side, expected_order_type):
            order_type, order_price, side, _, _, _, _, _, _ = await create_order._get_order_details(
                null_context, "market", side, None, None, None
            )
            assert order_type is expected_order_type
            assert order_price == ten
            assert side is None
            get_offset_mock.assert_called_once_with(null_context, "0")
            get_offset_mock.reset_mock()
        await _test_market(trading_enums.TradeOrderSide.SELL.value, trading_enums.TraderOrderType.SELL_MARKET)
        await _test_market(trading_enums.TradeOrderSide.BUY.value, trading_enums.TraderOrderType.BUY_MARKET)

        async def _test_limit(side, expected_order_type):
            order_type, order_price, side, _, _, _, _, _, _ = await create_order._get_order_details(
                null_context, "limit", side, "25%", None, None
            )
            assert order_type is expected_order_type
            assert order_price == ten
            assert side is None
            get_offset_mock.assert_called_once_with(null_context, "25%")
            get_offset_mock.reset_mock()
        await _test_limit(trading_enums.TradeOrderSide.SELL.value, trading_enums.TraderOrderType.SELL_LIMIT)
        await _test_limit(trading_enums.TradeOrderSide.BUY.value, trading_enums.TraderOrderType.BUY_LIMIT)

        async def _test_stop_loss(side, expected_side):
            order_type, order_price, side, _, _, _, _, _, _ = await create_order._get_order_details(
                null_context, "stop_loss", side, "25%", None, None
            )
            assert order_type is trading_enums.TraderOrderType.STOP_LOSS
            assert order_price == ten
            assert side is expected_side
            get_offset_mock.assert_called_once_with(null_context, "25%")
            get_offset_mock.reset_mock()
        await _test_stop_loss(trading_enums.TradeOrderSide.SELL.value, trading_enums.TradeOrderSide.SELL)
        await _test_stop_loss(trading_enums.TradeOrderSide.BUY.value, trading_enums.TradeOrderSide.BUY)

        async def _test_trailing_market(side, expected_side):
            order_type, order_price, side, _, trailing_method, _, _, _, _ = await create_order._get_order_details(
                null_context, "trailing_market", side, "25%", None, None
            )
            assert order_type is trading_enums.TraderOrderType.TRAILING_STOP
            assert trailing_method == "continuous"
            assert order_price == ten
            assert side is expected_side
            get_offset_mock.assert_called_once_with(null_context, "25%")
            get_offset_mock.reset_mock()
        await _test_trailing_market(trading_enums.TradeOrderSide.SELL.value, trading_enums.TradeOrderSide.SELL)
        await _test_trailing_market(trading_enums.TradeOrderSide.BUY.value, trading_enums.TradeOrderSide.BUY)

        async def _test_trailing_limit(side, expected_side):
            order_type, order_price, side, _, trailing_method, min_offset_val, max_offset_val, _, _ \
                = await create_order._get_order_details(
                null_context, "trailing_limit", side, "25%", None, None
            )
            assert order_type is trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            assert trailing_method == "continuous"
            assert order_price is None
            assert side is expected_side
            assert min_offset_val == ten
            assert max_offset_val == ten
            assert get_offset_mock.call_count == 2
            get_offset_mock.reset_mock()
        await _test_trailing_limit(trading_enums.TradeOrderSide.SELL.value, trading_enums.TradeOrderSide.SELL)
        await _test_trailing_limit(trading_enums.TradeOrderSide.BUY.value, trading_enums.TradeOrderSide.BUY)


async def test_create_order(mock_context, symbol_market):
    with mock.patch.object(trading_personal_data, "get_pre_order_data",
                           mock.AsyncMock(return_value=(None, None, decimal.Decimal(5), decimal.Decimal(105),
                                                        symbol_market))) \
        as get_pre_order_data_mock, \
         mock.patch.object(create_order, "_get_group_adapted_quantity", mock.Mock(return_value=decimal.Decimal(1))) \
            as _get_group_adapted_quantity_mock:

        # without linked orders
        # don't plot orders
        mock_context.plot_orders = False
        orders = await create_order._create_order(
            mock_context, "BTC/USDT", decimal.Decimal(1), decimal.Decimal(100), "tag",
            "order_type_name", "input_side", trading_enums.TradeOrderSide.BUY.value, None,
            trading_enums.TraderOrderType.BUY_MARKET, None, None, False, None, None,
            None, None, None, None,
            None, None, None, None,
            None, True, None)
        assert get_pre_order_data_mock.call_count == 2
        _get_group_adapted_quantity_mock.assert_called_once_with(mock_context, None,
                                                                 trading_enums.TraderOrderType.BUY_MARKET,
                                                                 decimal.Decimal(1))
        assert len(orders) == 1
        assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].tag == "tag"
        assert orders[0].origin_price == decimal.Decimal(105)
        assert orders[0].origin_quantity == decimal.Decimal(1)
        assert mock_context.just_created_orders == orders
        mock_context.just_created_orders = []
        get_pre_order_data_mock.reset_mock()
        _get_group_adapted_quantity_mock.reset_mock()

        # with order group
        # plot orders
        mock_context.plot_orders = True
        oco_group = grouping.create_one_cancels_the_other_group(mock_context)
        orders = await create_order._create_order(
            mock_context, "BTC/USDT", decimal.Decimal(1), decimal.Decimal(100), "tag2",
            "order_type_name", "input_side", trading_enums.TradeOrderSide.BUY.value, None,
            trading_enums.TraderOrderType.TRAILING_STOP, decimal.Decimal(5), None, False, oco_group,
            None, None, None, None,
            None, None, None, None,
            None, True, None, None)
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol="BTC/USDT",
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
        _get_group_adapted_quantity_mock.assert_called_once_with(mock_context, oco_group,
                                                                 trading_enums.TraderOrderType.TRAILING_STOP,
                                                                 decimal.Decimal(1))
        assert len(orders) == 1
        assert isinstance(orders[0], trading_personal_data.TrailingStopOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].tag == "tag2"
        assert orders[0].origin_price == decimal.Decimal(100)
        assert orders[0].origin_quantity == decimal.Decimal(1)
        assert orders[0].trader == mock_context.trader
        assert orders[0].trailing_percent == decimal.Decimal(5)
        assert orders[0].order_group is oco_group
        assert mock_context.just_created_orders == orders
        mock_context.just_created_orders = []
        get_pre_order_data_mock.reset_mock()
        _get_group_adapted_quantity_mock.reset_mock()

        # with same order group as one previously created order: group them together
        oco_group = grouping.create_one_cancels_the_other_group(mock_context)
        previous_orders = [trading_personal_data.LimitOrder(mock_context.trader),
                           trading_personal_data.LimitOrder(mock_context.trader)]
        previous_orders[0].add_to_order_group(oco_group)
        # with mock.patch.object(create_order, "pre_initialize_order_callback", mock.AsyncMock()) \
        #      as pre_initialize_order_callback_mock:
        mock_context.plot_orders = False
        orders = await create_order._create_order(
            mock_context, "BTC/USDT", decimal.Decimal(1), decimal.Decimal(100), "tag2",
            "order_type_name", "side", trading_enums.TradeOrderSide.BUY.value, trading_enums.TradeOrderSide.BUY,
            trading_enums.TraderOrderType.TRAILING_STOP,
            decimal.Decimal(5), None, True, oco_group,
            None, None, None, None,
            None, None, None, None,
            None, True, None, None)
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol="BTC/USDT",
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
        _get_group_adapted_quantity_mock.assert_called_once_with(mock_context, oco_group,
                                                                 trading_enums.TraderOrderType.TRAILING_STOP,
                                                                 decimal.Decimal(1))
        assert len(orders) == 1
        assert isinstance(orders[0], trading_personal_data.TrailingStopOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].tag == "tag2"
        assert orders[0].origin_price == decimal.Decimal(100)
        assert orders[0].origin_quantity == decimal.Decimal(1)
        assert orders[0].trader == mock_context.trader
        assert orders[0].trailing_percent == decimal.Decimal(5)
        assert orders[0].order_group is oco_group
        assert orders[0].side is trading_enums.TradeOrderSide.BUY
        assert mock_context.just_created_orders == orders
        mock_context.just_created_orders = []

        grouped_orders = grouping.get_open_orders_from_group(oco_group)
        assert len(grouped_orders) == 1  # only order this order got created and therefore is open in group
        assert grouped_orders[0] is orders[0]


async def test_get_group_adapted_quantity(mock_context, skip_if_octobot_trading_mocking_disabled):
    # skip_if_octobot_trading_mocking_disabled btps_group, "can_create_order"
    oco_group = grouping.create_one_cancels_the_other_group(mock_context)
    # no filter on oco groups
    assert create_order._get_group_adapted_quantity(mock_context, oco_group, "whatever", decimal.Decimal(1000000)) \
           == decimal.Decimal(1000000)

    btps_group = grouping.create_balanced_take_profit_and_stop_group(mock_context)
    if os.getenv('CYTHON_IGNORE'):
        return
    with mock.patch.object(btps_group, "can_create_order", mock.Mock(return_value=False)) as can_create_order_mock, \
         mock.patch.object(btps_group, "get_max_order_quantity", mock.Mock(return_value=decimal.Decimal(1))) \
            as get_max_order_quantity_mock:
        # no context.just_created_orders: never block 1st orders to create as they can't be balanced
        assert create_order._get_group_adapted_quantity(mock_context, btps_group, "whatever", decimal.Decimal(100)) \
               == decimal.Decimal(100)
        can_create_order_mock.assert_not_called()
        get_max_order_quantity_mock.assert_not_called()

        order_1 = mock.Mock(order_group=oco_group, order_type=trading_enums.TraderOrderType.STOP_LOSS)
        mock_context.just_created_orders.append(order_1)
        # context.just_created_orders has orders from other groups: consider this one as 1st from the group
        assert create_order._get_group_adapted_quantity(mock_context, btps_group, "whatever", decimal.Decimal(100)) \
               == decimal.Decimal(100)
        can_create_order_mock.assert_not_called()
        get_max_order_quantity_mock.assert_not_called()

        order_2 = mock.Mock(order_group=btps_group, order_type=trading_enums.TraderOrderType.SELL_LIMIT)
        mock_context.just_created_orders.append(order_2)
        # only take profits being created: allow it
        assert create_order._get_group_adapted_quantity(mock_context, btps_group,
                                                        trading_enums.TraderOrderType.SELL_LIMIT,
                                                        decimal.Decimal(10)) \
               == decimal.Decimal(10)
        can_create_order_mock.assert_not_called()
        get_max_order_quantity_mock.assert_not_called()

        # imbalanced orders: call can_create_order to figure out if we can create this order
        assert create_order._get_group_adapted_quantity(mock_context, btps_group,
                                                        trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                                                        decimal.Decimal(10)) == decimal.Decimal(1)
        can_create_order_mock.assert_called_once_with(trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                                                      decimal.Decimal(10))
        get_max_order_quantity_mock.assert_called_once_with(trading_enums.TraderOrderType.STOP_LOSS_LIMIT)
