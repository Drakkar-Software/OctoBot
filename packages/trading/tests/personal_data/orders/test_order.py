#  Drakkar-Software OctoBot
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
import pytest
import decimal


import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.storage.orders_storage as orders_storage

from tests import event_loop
from tests.exchanges import exchange_manager, simulated_exchange_manager
from tests.exchanges.traders import trader_simulator
from tests.exchanges.traders import trader
from tests.test_utils.random_numbers import random_price

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_profitability(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    # Test filled_price > create_last_price
    # test side SELL
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.SELL
    order_filled_sup_side_sell_inst.filled_price = 10
    order_filled_sup_side_sell_inst.created_last_price = 9
    assert order_filled_sup_side_sell_inst.get_profitability() == (-(1 - 10 / 9))

    # test side BUY
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.BUY
    order_filled_sup_side_sell_inst.filled_price = 15.114778
    order_filled_sup_side_sell_inst.created_last_price = 7.265
    assert order_filled_sup_side_sell_inst.get_profitability() == (1 - 15.114778 / 7.265)

    # Test filled_price < create_last_price
    # test side SELL
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.SELL
    order_filled_sup_side_sell_inst.filled_price = 11.556877
    order_filled_sup_side_sell_inst.created_last_price = 20
    assert order_filled_sup_side_sell_inst.get_profitability() == (1 - 20 / 11.556877)

    # test side BUY
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.BUY
    order_filled_sup_side_sell_inst.filled_price = 8
    order_filled_sup_side_sell_inst.created_last_price = 14.35
    assert order_filled_sup_side_sell_inst.get_profitability() == (-(1 - 14.35 / 8))

    # Test filled_price == create_last_price
    # test side SELL
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.SELL
    order_filled_sup_side_sell_inst.filled_price = 1517374.4567
    order_filled_sup_side_sell_inst.created_last_price = 1517374.4567
    assert order_filled_sup_side_sell_inst.get_profitability() == 0

    # test side BUY
    order_filled_sup_side_sell_inst = personal_data.Order(trader_inst)
    order_filled_sup_side_sell_inst.side = enums.TradeOrderSide.BUY
    order_filled_sup_side_sell_inst.filled_price = 0.4275587387858527
    order_filled_sup_side_sell_inst.created_last_price = 0.4275587387858527
    assert order_filled_sup_side_sell_inst.get_profitability() == 0


async def test_update(trader):
    config, exchange_manager_inst, trader_inst = trader

    # with real trader
    order_inst = personal_data.Order(trader_inst)
    order_inst.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol="BTC/USDT",
                      current_price=10000,
                      quantity=1)

    assert order_inst.order_type == enums.TraderOrderType.BUY_MARKET
    assert order_inst.symbol == "BTC/USDT"
    assert order_inst.created_last_price == 10000
    assert order_inst.origin_quantity == 1
    assert order_inst.creation_time != 0
    assert order_inst.side is None
    assert order_inst.status == enums.OrderStatus.OPEN
    assert order_inst.filled_quantity != order_inst.origin_quantity
    assert order_inst.tag is None

    order_inst.update(order_type=enums.TraderOrderType.STOP_LOSS_LIMIT,
                      symbol="ETH/BTC",
                      quantity=0.1,
                      quantity_filled=5.2,
                      price=0.12,
                      stop_price=0.9,
                      tag="tag")
    assert order_inst.origin_stop_price == 0.9
    assert order_inst.origin_price == 0.12
    assert order_inst.tag == "tag"


async def test_simulated_update(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order_sim_inst = personal_data.Order(trader_inst)

    order_sim_inst.update(order_type=enums.TraderOrderType.SELL_MARKET,
                          symbol="LTC/USDT",
                          quantity=100,
                          price=3.22)
    assert order_sim_inst.status == enums.OrderStatus.OPEN
    order_sim_inst.origin_quantity == 100
    assert order_sim_inst.filled_quantity == 0

    order_sim_inst.update(quantity_filled=200)
    order_sim_inst.origin_quantity == 100
    assert order_sim_inst.filled_quantity == 200


async def test_initialize(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order_inst = personal_data.Order(trader_inst)
    order_inst.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(10000),
                      quantity=decimal.Decimal(1),
                      status=enums.OrderStatus.OPEN,
                      is_active=True)
    with mock.patch.object(order_inst, "update_order_status", mock.AsyncMock()) as update_order_status_mock, \
        mock.patch.object(order_inst, "_ensure_inactive_order_watcher", mock.AsyncMock()) as _ensure_inactive_order_watcher_mock:
        await order_inst.initialize()
        update_order_status_mock.assert_called_once()
        _ensure_inactive_order_watcher_mock.assert_not_called()

    inactive_order_inst = personal_data.Order(trader_inst)
    inactive_order_inst.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(10000),
                      quantity=decimal.Decimal(1),
                      status=enums.OrderStatus.OPEN,
                      is_active=False)
    with mock.patch.object(inactive_order_inst, "update_order_status", mock.AsyncMock()) as update_order_status_mock, \
        mock.patch.object(inactive_order_inst, "_ensure_inactive_order_watcher", mock.AsyncMock()) as _ensure_inactive_order_watcher_mock:
        await inactive_order_inst.initialize()
        update_order_status_mock.assert_called_once()
        _ensure_inactive_order_watcher_mock.assert_called_once()


async def test_order_state_creation(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order_inst = personal_data.Order(trader_inst)
    # errors.InvalidOrderState exception is caught by context manager
    with order_inst.order_state_creation():
        raise errors.InvalidOrderState()


async def test_parse_order_type():
    untyped_raw_order = {
        enums.ExchangeConstantsOrderColumns.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.ExchangeConstantsOrderColumns.TYPE.value: None,
    }
    untyped_raw_with_maker_order = {
        enums.ExchangeConstantsOrderColumns.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value: enums.ExchangeConstantsOrderColumns.MAKER.value,
        enums.ExchangeConstantsOrderColumns.TYPE.value: None,
    }
    typed_raw_order = {
        enums.ExchangeConstantsOrderColumns.SIDE.value: enums.TradeOrderSide.SELL.value,
        enums.ExchangeConstantsOrderColumns.TYPE.value: enums.TradeOrderType.MARKET,
    }
    assert personal_data.parse_order_type({}) == \
           (None, None)
    assert personal_data.parse_order_type(untyped_raw_order) == \
           (enums.TradeOrderSide.BUY, enums.TraderOrderType.UNKNOWN)
    assert personal_data.parse_order_type(untyped_raw_with_maker_order) == \
           (enums.TradeOrderSide.BUY, enums.TraderOrderType.BUY_LIMIT)
    untyped_raw_with_maker_order[enums.ExchangeConstantsOrderColumns.SIDE.value] = enums.TradeOrderSide.SELL.value
    assert personal_data.parse_order_type(untyped_raw_with_maker_order) == \
           (enums.TradeOrderSide.SELL, enums.TraderOrderType.SELL_LIMIT)
    assert personal_data.parse_order_type(typed_raw_order) == \
           (enums.TradeOrderSide.SELL, enums.TraderOrderType.SELL_MARKET)
    typed_raw_order[enums.ExchangeConstantsOrderColumns.TYPE.value] = enums.TradeOrderType.LIMIT
    assert personal_data.parse_order_type(typed_raw_order) == \
           (enums.TradeOrderSide.SELL, enums.TraderOrderType.SELL_LIMIT)


async def test_update_from_raw(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order_inst = personal_data.Order(trader_inst)
    # binance example market order
    raw_order = {
        'id': '362550114',
        'exchange_id': '123',
        'clientOrderId': 'x-T9698eeeeeeeeeeeeee792',
        'timestamp': 1637579281.377,
        'datetime': '2021-11-22T11:08:01.377Z',
        'lastTradeTimestamp': None,
        'symbol': 'UNI/USDT',
        'type': 'market',
        'timeInForce': 'GTC',
        'postOnly': False,
        'side': 'sell',
        'price': None,
        'stopPrice': None,
        'amount': 44964.0,
        'cost': None,
        'average': None,
        'filled': 44964.0,
        'remaining': 0.0,
        'status': 'closed',
        'fee': {'cost': 0.03764836, 'currency': 'USDT'},
        'trades': [],
        'fees': []
    }
    assert order_inst.update_from_raw(raw_order) is True
    assert order_inst.order_type is enums.TraderOrderType.SELL_MARKET
    assert order_inst.order_id == "362550114"
    assert order_inst.exchange_order_id == "123"
    assert order_inst.side is enums.TradeOrderSide.SELL
    assert order_inst.status is enums.OrderStatus.CLOSED
    assert order_inst.symbol == "UNI/USDT"
    assert order_inst.currency == "UNI"
    assert order_inst.market == "USDT"
    assert order_inst.taker_or_maker is enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
    assert order_inst.origin_price == constants.ZERO
    assert order_inst.origin_stop_price == constants.ZERO
    assert order_inst.origin_quantity == decimal.Decimal("44964.0")
    assert order_inst.filled_quantity == decimal.Decimal("44964.0")
    assert order_inst.filled_price == constants.ZERO
    assert order_inst.total_cost == constants.ZERO
    assert order_inst.created_last_price == constants.ZERO
    assert order_inst.timestamp == 1637579281.377
    assert order_inst.canceled_time == 0
    assert order_inst.executed_time == 1637579281.377
    assert order_inst.fee == {
        enums.FeePropertyColumns.COST.value: decimal.Decimal('0.03764836'),
        enums.FeePropertyColumns.CURRENCY.value: 'USDT',
        enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
    }

    order_inst = personal_data.Order(trader_inst)
    # binance example limit order
    raw_order = {
        'id': '362550114',
        'exchange_id': '123a',
        'clientOrderId': 'x-T9698eeeeeeeeeeeeee792',
        'timestamp': 1637579281.377,
        'datetime': '2021-11-22T11:08:01.377Z',
        'lastTradeTimestamp': None,
        'symbol': 'UNI/USDT',
        'type': 'limit',
        'timeInForce': 'GTC',
        'postOnly': False,
        'side': 'buy',
        'price': 12.664,
        'stopPrice': None,
        'amount': 44964.0,
        'cost': 123.6667,
        'average': 13,
        'filled': 44964.0,
        'remaining': 0.0,
        'status': 'closed',
        'fee': {'cost': 0.03764836, 'currency': 'USDT'},
        'trades': [],
        'fees': []
    }
    assert order_inst.update_from_raw(raw_order) is True
    assert order_inst.order_type is enums.TraderOrderType.BUY_LIMIT
    assert order_inst.order_id == "362550114"
    assert order_inst.exchange_order_id == "123a"
    assert order_inst.side is enums.TradeOrderSide.BUY
    assert order_inst.status is enums.OrderStatus.CLOSED
    assert order_inst.symbol == "UNI/USDT"
    assert order_inst.currency == "UNI"
    assert order_inst.market == "USDT"
    assert order_inst.taker_or_maker is enums.ExchangeConstantsMarketPropertyColumns.MAKER.value
    assert order_inst.origin_price == decimal.Decimal("12.664")
    assert order_inst.origin_stop_price == constants.ZERO
    assert order_inst.origin_quantity == decimal.Decimal("44964.0")
    assert order_inst.filled_quantity == decimal.Decimal("44964.0")
    assert order_inst.filled_price == decimal.Decimal("13")
    assert order_inst.total_cost == decimal.Decimal("123.6667")
    assert order_inst.created_last_price == decimal.Decimal("12.664")
    assert order_inst.timestamp == 1637579281.377
    assert order_inst.canceled_time == 0
    assert order_inst.executed_time == 1637579281.377
    assert order_inst.fee == {
        enums.FeePropertyColumns.COST.value: decimal.Decimal('0.03764836'),
        enums.FeePropertyColumns.CURRENCY.value: 'USDT',
        enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
    }


async def test_set_as_chained_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.Order(trader_inst)
    base_order.taker_or_maker = None

    with pytest.raises(errors.ConflictingOrdersError):
        await base_order.set_as_chained_order(base_order, True, {}, True)
    assert base_order.triggered_by is None
    assert base_order.has_been_bundled is False
    assert base_order.update_with_triggering_order_fees is False
    assert base_order.status is enums.OrderStatus.OPEN
    assert base_order.state is None
    assert base_order.taker_or_maker is None

    chained_order = personal_data.Order(trader_inst)
    await chained_order.set_as_chained_order(base_order, True, {}, True)
    assert chained_order.triggered_by is base_order
    assert chained_order.has_been_bundled is True
    assert base_order.update_with_triggering_order_fees is False
    assert chained_order.update_with_triggering_order_fees is True
    assert chained_order.taker_or_maker == "maker"
    assert chained_order.status is enums.OrderStatus.PENDING_CREATION
    assert isinstance(chained_order.state, personal_data.PendingCreationOrderState)


async def test_trigger_chained_orders(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.Order(trader_inst)
    # does nothing
    await base_order.on_filled(True)

    # with chained orders
    order_mock_1 = mock.Mock(
        update_price_if_outdated=mock.AsyncMock(),
        update_quantity_with_order_fees=mock.Mock(return_value=True),
        should_be_created=mock.Mock(return_value=True),
        is_cleared=mock.Mock(return_value=False)
    )
    order_mock_2 = mock.Mock(
        update_price_if_outdated=mock.AsyncMock(),
        update_quantity_with_order_fees=mock.Mock(return_value=True),
        should_be_created=mock.Mock(return_value=False),
        is_cleared=mock.Mock(return_value=False)
    )
    with mock.patch.object(base_order, "_create_triggered_chained_order", mock.AsyncMock()) as _create_triggered_chained_order_mock:

        base_order.add_chained_order(order_mock_1)
        base_order.add_chained_order(order_mock_2)

        # does not trigger chained orders
        await base_order.on_filled(False)
        order_mock_1.should_be_created.assert_not_called()
        order_mock_2.should_be_created.assert_not_called()
        order_mock_1.is_cleared.assert_not_called()
        order_mock_2.is_cleared.assert_not_called()
        order_mock_1.update_price_if_outdated.assert_not_called()
        order_mock_2.update_price_if_outdated.assert_not_called()
        order_mock_1.update_quantity_with_order_fees.assert_not_called()
        order_mock_2.update_quantity_with_order_fees.assert_not_called()
        _create_triggered_chained_order_mock.assert_not_called()

        # triggers chained orders
        await base_order.on_filled(True)
        order_mock_1.should_be_created.assert_called_once()
        order_mock_2.should_be_created.assert_called_once()
        order_mock_1.is_cleared.assert_called_once()
        order_mock_2.is_cleared.assert_called_once()
        order_mock_1.update_price_if_outdated.assert_called_once()
        order_mock_2.update_price_if_outdated.assert_called_once()
        order_mock_1.update_quantity_with_order_fees.assert_called_once()
        order_mock_2.update_quantity_with_order_fees.assert_called_once()
        # called only once: order_mock_2 should not be created
        _create_triggered_chained_order_mock.assert_called_once_with(order_mock_1, True)
        _create_triggered_chained_order_mock.reset_mock()
        order_mock_1.should_be_created.reset_mock()
        order_mock_2.should_be_created.reset_mock()
        order_mock_1.is_cleared.reset_mock()
        order_mock_2.is_cleared.reset_mock()
        order_mock_1.update_price_if_outdated.reset_mock()
        order_mock_2.update_price_if_outdated.reset_mock()
        order_mock_1.update_quantity_with_order_fees.reset_mock()
        order_mock_2.update_quantity_with_order_fees.reset_mock()

        # all orders should be created
        order_mock_2.should_be_created = mock.Mock(return_value=True)
        await base_order.on_filled(True)
        order_mock_1.should_be_created.assert_called_once()
        order_mock_2.should_be_created.assert_called_once()
        order_mock_1.is_cleared.assert_called_once()
        order_mock_2.is_cleared.assert_called_once()
        order_mock_1.update_price_if_outdated.assert_called_once()
        order_mock_2.update_price_if_outdated.assert_called_once()
        order_mock_1.update_quantity_with_order_fees.assert_called_once()
        order_mock_2.update_quantity_with_order_fees.assert_called_once()
        assert _create_triggered_chained_order_mock.call_count == 2
        _create_triggered_chained_order_mock.reset_mock()
        order_mock_1.should_be_created.reset_mock()
        order_mock_2.should_be_created.reset_mock()
        order_mock_1.is_cleared.reset_mock()
        order_mock_2.is_cleared.reset_mock()
        order_mock_1.update_price_if_outdated.reset_mock()
        order_mock_2.update_price_if_outdated.reset_mock()
        order_mock_1.update_quantity_with_order_fees.reset_mock()
        order_mock_2.update_quantity_with_order_fees.reset_mock()

        # order 1 has been cleared
        order_mock_1.is_cleared = mock.Mock(return_value=True)
        await base_order.on_filled(True)
        order_mock_1.should_be_created.assert_not_called()
        order_mock_2.should_be_created.assert_called_once()
        order_mock_1.is_cleared.assert_called_once()
        order_mock_2.is_cleared.assert_called_once()
        order_mock_1.update_price_if_outdated.assert_not_called()
        order_mock_2.update_price_if_outdated.assert_called_once()
        order_mock_1.update_quantity_with_order_fees.assert_not_called()
        order_mock_2.update_quantity_with_order_fees.assert_called_once()
        # called only once: order_mock_2 should not be created
        _create_triggered_chained_order_mock.assert_called_once_with(order_mock_2, True)


async def test_create_triggered_chained_order_mock(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.Order(trader_inst)
    eq_chained_order_1 = mock.Mock(get_name=mock.Mock(return_value="plop"))
    chained_order_1 = personal_data.Order(trader_inst)
    chained_order_1.create_triggered_equivalent_order = mock.AsyncMock(return_value=eq_chained_order_1)

    # normal call
    with mock.patch.object(order_util, "create_as_chained_order", mock.AsyncMock()) as create_as_chained_order_mock:
        await base_order._create_triggered_chained_order(chained_order_1, True)
        create_as_chained_order_mock.assert_called_once_with(chained_order_1)
        chained_order_1.create_triggered_equivalent_order.assert_not_called()

    # random error
    with mock.patch.object(
        order_util, "create_as_chained_order", mock.AsyncMock(side_effect=ZeroDivisionError)
    ) as create_as_chained_order_mock:
        # does not raise
        await base_order._create_triggered_chained_order(chained_order_1, False)
        create_as_chained_order_mock.assert_called_once_with(chained_order_1,)
        chained_order_1.create_triggered_equivalent_order.assert_not_called()

    # ExchangeClosedPositionError
    chained_order_1.status = None
    chained_order_1.state = mock.Mock()
    with mock.patch.object(
        order_util, "create_as_chained_order", mock.AsyncMock(side_effect=errors.ExchangeClosedPositionError)
    ) as create_as_chained_order_mock:
        # does not raise
        await base_order._create_triggered_chained_order(chained_order_1, False)
        create_as_chained_order_mock.assert_called_once_with(chained_order_1)
        assert chained_order_1.status == enums.OrderStatus.CLOSED
        assert chained_order_1.state is None
        assert chained_order_1.is_cleared()
        chained_order_1.create_triggered_equivalent_order.assert_not_called()

    # ExchangeOrderInstantTriggerError
    calls = []
    async def _create_as_chained_order(*_):
        if not calls:
            calls.append(1)
            raise errors.ExchangeOrderInstantTriggerError()
        return

    chained_order_1.status = 1
    chained_order_1.state = mock.Mock()
    with mock.patch.object(
        order_util, "create_as_chained_order", mock.AsyncMock(side_effect=_create_as_chained_order)
    ) as create_as_chained_order_mock, mock.patch.object(
        chained_order_1, "create_on_filled_artificial_order", mock.AsyncMock(
            return_value=mock.Mock(get_name=mock.Mock(return_value="plop"))
        )
    ) as create_on_filled_artificial_order_mock:
        await base_order._create_triggered_chained_order(chained_order_1, True)
        create_as_chained_order_mock.assert_called_once_with(chained_order_1)
        create_on_filled_artificial_order_mock.assert_called_once_with(True)
        assert chained_order_1.status == enums.OrderStatus.CLOSED
        assert chained_order_1.state is None
        assert chained_order_1.is_cleared()


async def test_are_simultaneously_triggered_grouped_orders_closed(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order = personal_data.Order(trader_inst)
    assert order._are_simultaneously_triggered_grouped_orders_closed() is False

    order_mock_1 = personal_data.Order(trader_inst)
    order_mock_1.triggered_by=order
    assert order_mock_1._are_simultaneously_triggered_grouped_orders_closed() is False

    group = "plop"
    equivalent_order_mock_2 = mock.Mock(
        order_group=group,
        is_closed=mock.Mock(return_value=False),
        triggered_by=order,
    )
    order_mock_2 = personal_data.Order(trader_inst)
    order_mock_2.order_group=group
    order_mock_2.is_closed=mock.Mock(return_value=False)
    order_mock_2.on_filled_artificial_order=equivalent_order_mock_2
    order_mock_2.triggered_by=order
    order.chained_orders=[order_mock_1, order_mock_2]
    # not in the same group
    assert order_mock_1._are_simultaneously_triggered_grouped_orders_closed() is False
    assert order_mock_2._are_simultaneously_triggered_grouped_orders_closed() is False

    # in the same group, orders not closed & support grouping
    order_mock_1.order_group = group
    assert order_mock_1._are_simultaneously_triggered_grouped_orders_closed() is False
    assert order_mock_2._are_simultaneously_triggered_grouped_orders_closed() is False

    # in the same group, 1 order closed & support grouping
    equivalent_order_mock_2.is_closed=mock.Mock(return_value=True)
    assert order_mock_1._are_simultaneously_triggered_grouped_orders_closed() is True
    assert order_mock_2._are_simultaneously_triggered_grouped_orders_closed() is False  # 1 is not closed

    # in the same group, 1 order not closed & doesnt support grouping
    equivalent_order_mock_2.is_closed=mock.Mock(return_value=False)
    equivalent_order_mock_2.SUPPORTS_GROUPING=False
    order_mock_1.SUPPORTS_GROUPING=False
    assert order_mock_1._are_simultaneously_triggered_grouped_orders_closed() is True
    assert order_mock_2._are_simultaneously_triggered_grouped_orders_closed() is True


async def test_set_as_inactive(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    with mock.patch.object(
        base_order, "_ensure_inactive_order_watcher", mock.AsyncMock()
    ) as _ensure_inactive_order_watcher_mock:
        with pytest.raises(ValueError):
            await base_order.set_as_inactive(None)
        with pytest.raises(ValueError):
            await base_order.set_as_inactive(order_util.create_order_price_trigger(base_order, decimal.Decimal(1), None))
        with pytest.raises(ValueError):
            await base_order.set_as_inactive(order_util.create_order_price_trigger(base_order, None, True))
        _ensure_inactive_order_watcher_mock.assert_not_called()
        assert base_order.is_active is True
        assert base_order.active_trigger is None
        base_order.status = None
        base_order.canceled_time = None
        await base_order.set_as_inactive(order_util.create_order_price_trigger(base_order, decimal.Decimal(1), False))
        assert base_order.is_active is False
        assert base_order.active_trigger.trigger_price == decimal.Decimal(1)
        assert base_order.active_trigger.trigger_above is False
        assert base_order.active_trigger.trigger_above is False
        base_order.status = enums.OrderStatus.OPEN
        base_order.canceled_time = 0
        _ensure_inactive_order_watcher_mock.assert_called_once()


async def test_ensure_inactive_order_watcher_and_sub_functions(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    assert base_order.active_trigger is None

    # does nothing, order is active
    await base_order._ensure_inactive_order_watcher()
    assert base_order.active_trigger is None

    trader_inst.enable_inactive_orders = False
    # does nothing, order can't be inactive
    await base_order._ensure_inactive_order_watcher()
    assert base_order.active_trigger is None

    trader_inst.enable_inactive_orders = True
    base_order.is_active = False

    # does nothing, order is a chained order that is not yet triggered
    base_order.is_waiting_for_chained_trigger = True
    await base_order._ensure_inactive_order_watcher()
    assert base_order.active_trigger is None
    base_order.is_waiting_for_chained_trigger = False

    # does nothing, order.active_trigger is None
    await base_order._ensure_inactive_order_watcher()
    assert base_order.active_trigger is None

    base_order.use_active_trigger(order_util.create_order_price_trigger(base_order, decimal.Decimal(1), True))

    # init event and task
    await base_order._ensure_inactive_order_watcher()
    event = base_order.active_trigger._trigger_event
    task = base_order.active_trigger._trigger_task
    assert not event.is_set()
    assert not task.done()
    assert len(exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(base_order.symbol).price_events_manager.events) == 1

    # call again, does not change task / event
    await base_order._ensure_inactive_order_watcher()
    assert event is base_order.active_trigger._trigger_event
    assert task is base_order.active_trigger._trigger_task

    base_order.clear()
    # event and task are removed
    assert base_order.active_trigger._trigger_task is None
    assert len(exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(base_order.symbol).price_events_manager.events) == 0

    base_order = personal_data.Order(trader_inst)
    base_order.is_active = False
    assert base_order.active_trigger is None
    base_order.use_active_trigger(order_util.create_order_price_trigger(base_order, decimal.Decimal(1), True))
    # now is_synchronization_enabled returns False
    exchange_manager_inst.exchange_personal_data.orders_manager.enable_order_auto_synchronization = False
    await base_order._ensure_inactive_order_watcher()
    assert base_order.active_trigger._trigger_event is None
    assert base_order.active_trigger._trigger_task is None
    assert len(exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(base_order.symbol).price_events_manager.events) == 0

    base_order.clear()
    # event and task are removed
    assert base_order.active_trigger._trigger_event is None
    assert base_order.active_trigger._trigger_task is None
    assert len(exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(base_order.symbol).price_events_manager.events) == 0


def test_should_become_active(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    assert base_order.should_become_active(123, decimal.Decimal(1)) is False    # is active

    base_order.is_active = False
    base_order.use_active_trigger(order_util.create_order_price_trigger(base_order, decimal.Decimal("0.5"), True))
    base_order.creation_time = 123
    assert base_order.should_become_active(124, decimal.Decimal(1)) is True
    assert base_order.should_become_active(123, decimal.Decimal(1)) is True
    assert base_order.should_become_active(122, decimal.Decimal(1)) is False
    assert base_order.should_become_active(123, decimal.Decimal("0.4")) is False

    base_order.active_trigger.trigger_above = False
    assert base_order.should_become_active(123, decimal.Decimal("0.4")) is True
    assert base_order.should_become_active(123, decimal.Decimal("1.4")) is False


async def test_on_active_trigger(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    with mock.patch.object(order_util, "create_as_active_order_using_strategy_if_any", mock.Mock()) as create_as_active_order_using_strategy_if_any_mock:
        # order is active already
        await base_order.on_active_trigger(123, "callback")
        create_as_active_order_using_strategy_if_any_mock.assert_not_called()

        base_order.is_active = False
        await base_order.on_active_trigger(123, "callback")
        create_as_active_order_using_strategy_if_any_mock.assert_called_once_with(base_order, 123, "callback")


async def test_on_inactive_from_active(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    base_order.is_active = True
    state_mock = mock.Mock(clear=mock.Mock())
    base_order.state = state_mock
    with mock.patch.object(base_order, "_ensure_inactive_order_watcher", mock.AsyncMock()) as _ensure_inactive_order_watcher_mock:
        with pytest.raises(ValueError):
            # missing active trigger values
            await base_order.on_inactive_from_active()
        assert base_order.is_active is True
        assert base_order.state == state_mock
        _ensure_inactive_order_watcher_mock.assert_not_called()
        base_order.state.clear.assert_not_called()

        base_order.use_active_trigger(order_util.create_order_price_trigger(base_order, decimal.Decimal(1), True))
        await base_order.on_inactive_from_active()
        assert base_order.is_active is False
        base_order.state.clear.assert_called_once()
        _ensure_inactive_order_watcher_mock.assert_called_once()


async def test_on_active_from_inactive(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    base_order = personal_data.Order(trader_inst)
    base_order.is_active = False
    with mock.patch.object(base_order, "clear", mock.Mock()) as clear_mock:
        await base_order.on_active_from_inactive()
        assert base_order.is_active is True
        clear_mock.assert_called_once()


async def test_create_on_filled_artificial_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.Order(trader_inst)
    base_order.origin_quantity = decimal.Decimal(11)
    base_order.order_group = "plop group"
    base_order.symbol = "BTC/USDT"
    base_order.reduce_only = True
    assert await base_order.create_on_filled_artificial_order(False) is None


    base_order = personal_data.StopLossOrder(trader_inst)
    base_order.origin_quantity = decimal.Decimal(11)
    base_order.origin_stop_price = decimal.Decimal(2000)
    base_order.order_group = "plop group"
    base_order.symbol = "BTC/USDT"
    base_order.reduce_only = True
    base_order.close_position = False

    # simulation: disabled
    assert await base_order.create_on_filled_artificial_order(True) is None

    # disable simulation
    trader_inst.simulate = False
    trader_inst.allow_artificial_orders = False

    async def _create_new_order(order, *_, **__):
        return order

    with mock.patch.object(
        trader_inst, "_create_new_order", mock.AsyncMock(side_effect=_create_new_order)
    ) as _create_new_order_mock:
        triggered_artificial_order = await base_order.create_on_filled_artificial_order(True)
        _create_new_order_mock.assert_called_once()

        assert isinstance(triggered_artificial_order, personal_data.SellMarketOrder)
        assert triggered_artificial_order.origin_quantity == decimal.Decimal(11)
        assert triggered_artificial_order.created_last_price == decimal.Decimal(2000)
        assert triggered_artificial_order.order_group == "plop group"
        assert triggered_artificial_order.symbol == "BTC/USDT"
        assert triggered_artificial_order.reduce_only == True
        assert triggered_artificial_order.close_position == False
        assert base_order.on_filled_artificial_order is triggered_artificial_order


def test_update_quantity_with_order_fees(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.Order(trader_inst)
    base_order.symbol = "BTC/USDT"

    other_order = personal_data.Order(trader_inst)
    other_order.symbol = base_order.symbol
    other_order.origin_quantity = decimal.Decimal(1)

    # case 1: quantity_currency is not the amount unit: nothing changes
    base_order.fee = {
        enums.FeePropertyColumns.CURRENCY.value: "USDT",
        enums.FeePropertyColumns.COST.value: decimal.Decimal("1")
    }
    other_order.quantity_currency = "BTC"
    assert other_order.update_quantity_with_order_fees(base_order) is True
    assert other_order.origin_quantity == decimal.Decimal(1)    # nothing changed

    # case 2: quantity_currency is the amount unit: other_order quantity is reduced
    base_order.fee = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1")
    }
    other_order.quantity_currency = "BTC"
    assert other_order.update_quantity_with_order_fees(base_order) is True
    assert other_order.origin_quantity == decimal.Decimal("0.9")    # 1 - 0.1
    other_order.origin_quantity = decimal.Decimal(1)

    # case 3: quantity_currency is the amount unit and is too large: return False
    base_order.fee = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: decimal.Decimal("1")
    }
    other_order.quantity_currency = "BTC"
    assert other_order.update_quantity_with_order_fees(base_order) is False
    assert other_order.origin_quantity == decimal.Decimal(1)    # nothing changed
    base_order.fee = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: decimal.Decimal("1.1")
    }
    other_order.quantity_currency = "BTC"
    assert other_order.update_quantity_with_order_fees(base_order) is False
    assert other_order.origin_quantity == decimal.Decimal(1)    # nothing changed

    # case 4: quantity_currency is the amount unit: other_order quantity is reduced and adapted
    base_order.fee = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: decimal.Decimal("0.111111111111111111111111")
    }
    other_order.quantity_currency = "BTC"
    assert other_order.update_quantity_with_order_fees(base_order) is True
    # 1 - 0.111111111111111111111111 with truncated digits
    assert other_order.origin_quantity == decimal.Decimal("0.88888")
    other_order.origin_quantity = decimal.Decimal(1)


async def test_update_from_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order_1 = personal_data.Order(trader_inst)
    base_order_1.order_id = "1"
    base_order_1.exchange_order_id = "1a"
    base_order_1.status = enums.OrderStatus.OPEN
    base_order_1.filled_price = decimal.Decimal("2")

    base_order_2 = personal_data.Order(trader_inst)
    base_order_2.order_id = "2"
    base_order_2.exchange_order_id = "2a"
    base_order_2.status = enums.OrderStatus.CLOSED
    base_order_2.filled_price = decimal.Decimal("3")

    # no state
    await base_order_1.update_from_order(base_order_2)
    assert base_order_1.order_id == "2"
    assert base_order_1.exchange_order_id == "2a"
    assert base_order_1.status == enums.OrderStatus.CLOSED
    assert base_order_1.filled_price == decimal.Decimal("3")

    # with state
    state_1 = personal_data.OpenOrderState(base_order_1, False)
    state_2 = personal_data.OpenOrderState(base_order_2, False)
    base_order_1.state = state_1
    base_order_2.state = state_2
    base_order_2.order_id = "3"
    base_order_2.exchange_order_id = "3AAAAA"
    base_order_2.status = enums.OrderStatus.CANCELED
    base_order_2.filled_price = decimal.Decimal("4")
    await base_order_1.update_from_order(base_order_2)
    assert base_order_1.order_id == "3"
    assert base_order_1.exchange_order_id == "3AAAAA"
    assert base_order_1.status == enums.OrderStatus.CANCELED
    assert base_order_1.filled_price == decimal.Decimal("4")
    assert base_order_1.state is state_2
    assert base_order_1.state.order is base_order_1


async def test_update_from_order_storage(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    order = personal_data.BuyLimitOrder(trader_inst)
    order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                 symbol="BTC/USDT",
                 current_price=decimal.Decimal("70"),
                 quantity=decimal.Decimal("10"),
                 price=decimal.Decimal("70"),
                 exchange_order_id="PLOP",
                 active_trigger=personal_data.create_order_price_trigger(order, decimal.Decimal("70"), True))
    origin_tag = order.tag
    origin_trader_creation_kwargs = order.trader_creation_kwargs
    origin_exchange_creation_params = order.exchange_creation_params
    origin_order_id = order.order_id
    origin_exchange_order_id = order.exchange_order_id
    origin_has_been_bundled = order.has_been_bundled
    origin_associated_entry_ids = order.associated_entry_ids
    origin_update_with_triggering_order_fees = order.update_with_triggering_order_fees

    # wrong format
    order.update_from_storage_order_details({"hello": "hi there"})
    assert order.tag is origin_tag
    assert order.trader_creation_kwargs is origin_trader_creation_kwargs
    assert order.exchange_creation_params is origin_exchange_creation_params
    assert order.order_id is origin_order_id
    assert order.exchange_order_id is origin_exchange_order_id
    assert order.has_been_bundled is origin_has_been_bundled
    assert order.associated_entry_ids is origin_associated_entry_ids
    assert order.broker_applied is False
    assert order.update_with_triggering_order_fees is origin_update_with_triggering_order_fees

    # partial update
    order.update_from_storage_order_details({
        enums.StoredOrdersAttr.TRADER_CREATION_KWARGS.value: {"plop": 1}
    })
    assert order.tag is origin_tag
    assert order.trader_creation_kwargs == {"plop": 1} != origin_trader_creation_kwargs
    assert order.exchange_creation_params is origin_exchange_creation_params
    assert order.order_id is origin_order_id
    assert order.exchange_order_id is origin_exchange_order_id
    assert order.has_been_bundled is origin_has_been_bundled
    assert order.associated_entry_ids is origin_associated_entry_ids
    assert order.update_with_triggering_order_fees is origin_update_with_triggering_order_fees
    assert order.active_trigger.trigger_price == decimal.Decimal(70)
    assert order.active_trigger.trigger_above is True
    assert order.is_active is True

    # full update
    order.update_from_storage_order_details({
        constants.STORAGE_ORIGIN_VALUE: {
            enums.ExchangeConstantsOrderColumns.TAG.value: "t1",
            enums.ExchangeConstantsOrderColumns.ID.value: "11a",
            enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "eee1",
            enums.ExchangeConstantsOrderColumns.BROKER_APPLIED.value: True,
            enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value: "taker",
            enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value: False,
        },
        enums.StoredOrdersAttr.TRADER_CREATION_KWARGS.value: {"plop2": 1},
        enums.StoredOrdersAttr.EXCHANGE_CREATION_PARAMS.value: {"ex": 2, "gg": "yesyes"},
        enums.StoredOrdersAttr.HAS_BEEN_BUNDLED.value: True,
        enums.StoredOrdersAttr.ENTRIES.value: ["ABC", "2"],
        enums.StoredOrdersAttr.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        enums.StoredOrdersAttr.ACTIVE_TRIGGER.value: {
            enums.StoredOrdersAttr.ACTIVE_TRIGGER_PRICE.value: 32,
            enums.StoredOrdersAttr.ACTIVE_TRIGGER_ABOVE.value: False,
        },
    })
    assert order.tag == "t1" != origin_tag
    assert order.trader_creation_kwargs == {"plop2": 1} != origin_trader_creation_kwargs
    assert order.exchange_creation_params == {"ex": 2, "gg": "yesyes"} != origin_exchange_creation_params
    assert order.order_id == "11a" != origin_order_id
    assert order.broker_applied is True
    assert order.taker_or_maker == "taker"
    assert order.exchange_order_id == "eee1" != origin_exchange_order_id
    assert order.has_been_bundled is True is not origin_has_been_bundled
    assert order.associated_entry_ids == ["ABC", "2"] != origin_associated_entry_ids
    assert order.has_been_bundled is True is not origin_has_been_bundled
    assert order.update_with_triggering_order_fees is True is not origin_update_with_triggering_order_fees
    assert order.is_active is False
    assert order.active_trigger.trigger_price == decimal.Decimal(32)
    assert order.active_trigger.trigger_above is False


async def test_is_counted_in_available_funds(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    order = personal_data.BuyLimitOrder(trader_inst)
    order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                 symbol="BTC/USDT",
                 current_price=decimal.Decimal("70"),
                 quantity=decimal.Decimal("10"),
                 price=decimal.Decimal("70"),
                 exchange_order_id="PLOP",
                 active_trigger=personal_data.create_order_price_trigger(order, decimal.Decimal("70"), True))
    assert order.is_counted_in_available_funds() is True

    # is_active
    order.is_active = False
    assert order.is_counted_in_available_funds() is False
    order.is_active = True
    assert order.is_counted_in_available_funds() is True

    # simulated order
    trader_inst.simulate = True
    assert order.is_counted_in_available_funds() is True
    for order_type in [enums.TraderOrderType.BUY_LIMIT, enums.TraderOrderType.SELL_LIMIT, enums.TraderOrderType.SELL_MARKET]:
        order.order_type = order_type
        assert order.is_counted_in_available_funds() is True
    for order_type in [
        enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.STOP_LOSS_LIMIT, 
        enums.TraderOrderType.TAKE_PROFIT, enums.TraderOrderType.TAKE_PROFIT_LIMIT, enums.TraderOrderType.TRAILING_STOP
    ]:
        order.order_type = order_type
        assert order.is_counted_in_available_funds() is False

    order.order_type = enums.TraderOrderType.BUY_LIMIT

    # real order
    trader_inst.simulate = False
    # is_self_managed
    with mock.patch.object(order, "is_self_managed", mock.Mock(return_value=True)) as is_self_managed_mock:
        assert order.is_counted_in_available_funds() is False
        is_self_managed_mock.assert_called_once()
        is_self_managed_mock.reset_mock()
        is_self_managed_mock.return_value = False
        assert order.is_counted_in_available_funds() is True
        is_self_managed_mock.assert_called_once()

    trader_inst.simulate = True
    # state.is_already_counted_in_available_funds
    order.state = personal_data.OpenOrderState(order, False, is_already_counted_in_available_funds=True)
    assert order.is_counted_in_available_funds() is False
    order.state = personal_data.OpenOrderState(order, False, is_already_counted_in_available_funds=False)
    assert order.is_counted_in_available_funds() is True
