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
from mock import Mock, AsyncMock
import pytest

import octobot_trading.api as api
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.orders.order_factory as order_factory

from tests import event_loop
from tests.exchanges import future_simulated_exchange_manager, simulated_exchange_manager, set_future_exchange_fees
from tests.exchanges.traders import future_trader_simulator_with_default_linear, \
    future_trader_simulator_with_default_inverse, DEFAULT_FUTURE_SYMBOL, DEFAULT_FUTURE_FUNDING_RATE, trader_simulator


def test_get_min_max_amounts():
    # normal values
    symbol_market = {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.5,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 100,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: None,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: None
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 0.5,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 50
            },
        }
    }
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = personal_data.get_min_max_amounts(
        symbol_market)
    assert min_quantity == 0.5
    assert max_quantity == 100
    assert min_cost is None
    assert max_cost is None
    assert min_price == 0.5
    assert max_price == 50

    # missing all values
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = personal_data.get_min_max_amounts({})
    assert min_quantity is None
    assert max_quantity is None
    assert min_cost is None
    assert max_cost is None
    assert min_price is None
    assert max_price is None

    # missing all values: asign default
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = personal_data.get_min_max_amounts({}, "xyz")
    assert min_quantity == "xyz"
    assert max_quantity == "xyz"
    assert min_cost == "xyz"
    assert max_cost == "xyz"
    assert min_price == "xyz"
    assert max_price == "xyz"

    # missing values: assign default

    symbol_market = {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.5,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 100,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: None,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: None
            }
        }
    }
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = personal_data.get_min_max_amounts(symbol_market, "xyz")
    assert min_quantity == 0.5
    assert max_quantity == 100
    assert min_cost == "xyz"  # None is not a valid value => assign default
    assert max_cost == "xyz"  # None is not a valid value => assign default
    assert min_price == "xyz"
    assert max_price == "xyz"


def test_get_fees_for_currency():
    fee1 = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: 1
    }
    assert personal_data.get_fees_for_currency(fee1, "BTC") == 1
    assert personal_data.get_fees_for_currency(fee1, "BTC1") == 0

    fee2 = {
        enums.FeePropertyColumns.CURRENCY.value: "BTC",
        enums.FeePropertyColumns.COST.value: 0,
        enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True
    }
    assert personal_data.get_fees_for_currency(fee2, "BTC") == 0
    assert personal_data.get_fees_for_currency(fee2, "BTC1") == 0

    assert personal_data.get_fees_for_currency({}, "BTC") == 0
    assert personal_data.get_fees_for_currency(None, "BTC") == 0


def test_get_max_order_quantity_for_price_long_linear(future_trader_simulator_with_default_linear):
    # values also tested with bybit fees
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    default_contract.set_current_leverage(constants.ONE)
    # at price = 37000 and 9961.7672 USDT in stock, if there were no fees,
    # max quantity would be 9961.7672 / 37000 = 0.269236951351,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9961.7672"), decimal.Decimal("37000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('0.2691292996314987518506111069')

    default_contract.set_current_leverage(decimal.Decimal("2"))
    # at price = 37000 and 9961.7672 USDT in stock, if there were no fees,
    # max quantity would be 9961.7672 / 37000 * 2 = 0.538473902703,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9961.7672"), decimal.Decimal("37000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('0.5378285084925116886762911533')

    default_contract.set_current_leverage(decimal.Decimal("10"))
    # at price = 43500 and 9943.9078 USDT in stock, if there were no fees,
    # max quantity would be 9943.9078 / 43500 * 10 = 2.26311218138,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9943.9078"), decimal.Decimal("43500"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('2.268713592786774536511021980')

    # example from bybit docs
    # Trader place a long entry of 1BTC at USD8000 with 50x leverage.
    # Order Cost = 160USDT + 6USDT + 5.88USDT = 171.88 USDT
    default_contract.set_current_leverage(decimal.Decimal("50"))
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("171.88"), decimal.Decimal("8000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('1.033330126971912273951519815')
    # Here the max size is a bit higher than 1 since binance fees are a bit higher

    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    # at price = 43500 and 9943.9078 USDT in stock, if there were no fees,
    # max quantity would be 9943.9078 / 43500 * 100 = 22.6311218138,
    # it is actually less to allow fees (which are huge on 100x)
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9943.9078"), decimal.Decimal("43500"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('21.17409981559794389578089799')


def test_get_max_order_quantity_for_price_short_linear(future_trader_simulator_with_default_linear):
    # values also tested with bybit fees
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    # Differs from long due to the position closing fees at liquidation price which are higher (price is higher)
    # Therefore to open the same position size, more funds are required than for longs
    # (max quantity is lower than for longs)
    default_contract.set_current_leverage(constants.ONE)
    # at price = 37000 and 9961.7672 USDT in stock, if there were no fees,
    # max quantity would be 9961.7672 / 37000 = 0.269236951351,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9961.7672"), decimal.Decimal("37000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('0.2689142542462558443381455767')

    default_contract.set_current_leverage(decimal.Decimal("2"))
    # at price = 37000 and 9961.7672 USDT in stock, if there were no fees,
    # max quantity would be 9961.7672 / 37000 * 2 = 0.538473902703,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9961.7672"), decimal.Decimal("37000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('0.5373991044937152721583859308')

    default_contract.set_current_leverage(decimal.Decimal("50"))
    # at price = 44500 and 9943.9078 USDT in stock, if there were no fees,
    # max quantity would be 9943.9078 / 44500 * 50 = 11.1729301124,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9943.9078"), decimal.Decimal("44500"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('10.73907161895381638004397617')

    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    # at price = 37000 and 9961.7672 USDT in stock, if there were no fees,
    # max quantity would be 9961.7672 / 37000 * 100 = 26.9236951351,
    # it is actually less to allow fees (which are huge on 100x)
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.LinearPosition(trader_inst, default_contract),
        decimal.Decimal("9961.7672"), decimal.Decimal("37000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('24.92011767413470486406436055')


def test_get_max_order_quantity_for_price_long_inverse(future_trader_simulator_with_default_inverse):
    # values also tested with bybit fees
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    default_contract.set_current_leverage(constants.ONE)
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 = 36000,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('35956.85177786656012784658410')

    default_contract.set_current_leverage(decimal.Decimal("2"))
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 * 2 = 72000,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('71856.28742514970059880239519')

    default_contract.set_current_leverage(decimal.Decimal("25"))
    # example from bybit docs
    # Trader places a buy limit order of 10,000 BTCUSD contracts at 6,400 USD, using 25x leverage.
    # Order Cost = 0.0625 BTC (Initial margin) + 0.00117188 BTC (fee to open) + 0.00121872 BTC (fee to close) = 0.06489060 BTC
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        decimal.Decimal("0.06489060"), decimal.Decimal("6400"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('10174.92747941983535868286946')
    # higher than the 10000 from bybit example as binance fees are lower

    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 * 100 = 3600000,
    # it is actually less to allow fees (which are huge on 100x)
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('3332099.222510181414291003332')


def test_get_max_order_quantity_for_price_short_inverse(future_trader_simulator_with_default_inverse):
    # values also tested with bybit fees
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    # Differs from long due to the position closing fees at liquidation price which are higher (price is higher)
    # Therefore to open the same position size, less funds are required than for longs
    # (max quantity is higher than for longs)
    default_contract.set_current_leverage(constants.ONE)
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 = 36000,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('35985.60575769692123150739704')

    default_contract.set_current_leverage(decimal.Decimal("2"))
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 * 2 = 72000,
    # it is actually less to allow fees
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('71913.70355573312025569316820')

    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    # at price = 36000 and 1 btc in stock, if there were no fees,
    # max quantity would be 1 * 36000 * 100 = 3600000,
    # it is actually less to allow fees (which are huge on 100x)
    assert personal_data.get_max_order_quantity_for_price(
        personal_data.InversePosition(trader_inst, default_contract),
        constants.ONE, decimal.Decimal("36000"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('3334568.358651352352723230826')


@pytest.mark.asyncio
async def test_get_futures_max_order_size(future_trader_simulator_with_default_linear):
    # values also tested with bybit fees
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    symbol = default_contract.pair
    api.force_set_mark_price(exchange_manager_inst, symbol, 37000)
    compare_accuracy = decimal.Decimal("1.000000")

    default_contract.set_current_leverage(constants.ONE)
    l1_current_symbol_holding, _, l1_market_quantity, _, _ = \
        await personal_data.get_pre_order_data(exchange_manager_inst, symbol=symbol)
    assert personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.BUY,
        decimal.Decimal("37000"), False, l1_current_symbol_holding, l1_market_quantity
    ) == (decimal.Decimal('0.02701622053881150242605660439'), True)

    # take leverage into account
    default_contract.set_current_leverage(decimal.Decimal(5))
    l2_current_symbol_holding, _, l2_market_quantity, _, _ = \
        await personal_data.get_pre_order_data(exchange_manager_inst, symbol=symbol)
    assert l2_current_symbol_holding.quantize(compare_accuracy) == \
           (l1_current_symbol_holding * default_contract.current_leverage).quantize(compare_accuracy)
    assert l2_market_quantity.quantize(compare_accuracy) == \
           (l1_market_quantity * default_contract.current_leverage).quantize(compare_accuracy)
    full_buy_size, increasing = personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.BUY,
        decimal.Decimal("37000"), False, l2_current_symbol_holding, l2_market_quantity
    )
    assert (full_buy_size, increasing) == (decimal.Decimal('0.1346503937177512307045985802'), True)

    # reduce only (position is empty)
    assert personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.BUY,
        decimal.Decimal("37000"), True, l2_current_symbol_holding, l2_market_quantity
    ) == (constants.ZERO, False)

    # with short position
    full_sell_size, increasing = personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.SELL,
        decimal.Decimal("37000"), False, l2_current_symbol_holding, l2_market_quantity
    )
    assert (full_sell_size, increasing) == (decimal.Decimal('0.1345431452958334678764786291'), True)
    # reduce only (position is empty)
    assert personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.SELL,
        decimal.Decimal("37000"), True, l2_current_symbol_holding, l2_market_quantity
    ) == (constants.ZERO, False)

    # LONG POSITION
    # reduce only (position is NOT empty)
    position = exchange_manager_inst.exchange_personal_data.positions_manager.get_symbol_positions(symbol)[0]
    await position.update(mark_price=decimal.Decimal(37000), update_margin=decimal.Decimal(4))
    # position is now long
    position_size = position.size
    assert position_size == decimal.Decimal("0.0005405405405405405405405405405")
    assert personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.SELL,
        decimal.Decimal("37000"), True, l2_current_symbol_holding, l2_market_quantity
    ) == (position_size, False)

    # not reduce only and long position: can reverse position
    position_size = position.size
    assert position_size == decimal.Decimal("0.0005405405405405405405405405405")    # still the same size
    max_size, increasing = personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.SELL,
        decimal.Decimal("37000"), False, l2_current_symbol_holding, l2_market_quantity
    )
    assert increasing is True
    assert max_size > position_size
    # higher than when just opening a position with full free funds
    assert max_size > full_sell_size
    assert max_size == decimal.Decimal("0.1352986545732659722297027996")

    # SHORT POSITION
    # reduce only (position is NOT empty)
    await position.update(mark_price=decimal.Decimal(37000), update_margin=decimal.Decimal(-500))
    # position is now short
    position_size = position.size
    assert position_size == decimal.Decimal("-0.06702702702702702702702702703")
    assert personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.BUY,
        decimal.Decimal("37000"), True, l2_current_symbol_holding, l2_market_quantity
    ) == (-position_size, False)

    # not reduce only and short position: can reverse position
    position_size = position.size
    assert position_size == decimal.Decimal("-0.06702702702702702702702702703")    # still the same size
    max_size, increasing = personal_data.get_futures_max_order_size(
        exchange_manager_inst, symbol, enums.TradeOrderSide.BUY,
        decimal.Decimal("37000"), False, l2_current_symbol_holding, l2_market_quantity
    )
    assert increasing is True
    assert max_size > abs(position_size)
    # higher than when just opening a position with full free funds
    assert max_size > full_sell_size
    assert max_size == decimal.Decimal("0.2149168523362071749168523362")


@pytest.mark.asyncio
async def test_create_as_chained_order_regular_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.BuyLimitOrder(trader_inst)
    base_order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal("70"),
                      quantity=decimal.Decimal("10"),
                      price=decimal.Decimal("70"))
    base_order.is_waiting_for_chained_trigger = True
    base_order.creation_time = 123
    origin_time = base_order.creation_time
    assert base_order.to_dict()[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] \
           == origin_time
    # base_order.state is None since no state has been associated to it (not initiliazed)
    assert base_order.state is None
    assert base_order.is_initialized is False

    await personal_data.create_as_chained_order(base_order)
    assert base_order.creation_time > origin_time   # creation_time got update using current time
    assert base_order.is_waiting_for_chained_trigger is False
    assert base_order.is_created() is True
    assert base_order.is_initialized is True
    assert isinstance(base_order.state, personal_data.OpenOrderState)

    # use chained order creation time
    assert base_order.to_dict()[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] \
           == base_order.creation_time


@pytest.mark.asyncio
async def test_create_as_chained_order_inactive_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    trader_inst.enable_inactive_orders = True

    base_order = personal_data.BuyLimitOrder(trader_inst)
    base_order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal("70"),
                      quantity=decimal.Decimal("10"),
                      price=decimal.Decimal("70"))
    trigger = order_util.create_order_price_trigger(base_order, decimal.Decimal("90"), True)
    with mock.patch.object(trigger, "create_watcher", mock.AsyncMock(wraps=trigger.create_watcher)) as create_watcher_mock:
        base_order.is_waiting_for_chained_trigger = True
        await base_order.set_as_inactive(trigger)
        # not called for untriggered chained order when they are set as inactive
        create_watcher_mock.assert_not_called()
        base_order.creation_time = 123
        origin_time = base_order.creation_time
        assert base_order.to_dict()[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] \
            == origin_time
        # base_order.state is None since no state has been associated to it (not initiliazed)
        assert base_order.state is None
        assert base_order.is_initialized is False

        await personal_data.create_as_chained_order(base_order) # will call initialize which will call create_watcher
        assert base_order.creation_time > origin_time   # creation_time got update using current time
        assert base_order.is_waiting_for_chained_trigger is False
        assert base_order.is_created() is True
        assert base_order.is_initialized is True
        assert isinstance(base_order.state, personal_data.OpenOrderState)
        # called for triggered chained order when they are created as triggered chained orders
        create_watcher_mock.assert_awaited_once_with(
            exchange_manager_inst, base_order.symbol, base_order.creation_time
        )

        # use chained order creation time
        assert base_order.to_dict()[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] \
            == base_order.creation_time


@pytest.mark.asyncio
async def test_create_as_chained_order_bundled_order_no_open_order(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    base_order = personal_data.BuyLimitOrder(trader_inst)
    base_order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal("70"),
                      quantity=decimal.Decimal("10"),
                      price=decimal.Decimal("70"))
    base_order.has_been_bundled = True
    # base_order.state is None since no state has been associated to it (not initiliazed)
    assert base_order.state is None
    assert base_order.is_initialized is False

    #no order in order_manager, register as pending order
    assert not exchange_manager_inst.exchange_personal_data.orders_manager.orders
    assert not exchange_manager_inst.exchange_personal_data.orders_manager.pending_creation_orders

    # simulate real trader
    trader_inst.simulate = False
    await personal_data.create_as_chained_order(base_order)
    # did not add it to orders
    assert not exchange_manager_inst.exchange_personal_data.orders_manager.orders
    assert exchange_manager_inst.exchange_personal_data.orders_manager.pending_creation_orders == [base_order]

    assert base_order.is_waiting_for_chained_trigger is False
    # still not initialized
    assert base_order.is_initialized is False


@pytest.mark.asyncio
async def test_create_as_chained_order_bundled_order_with_open_orders(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator

    open_order_1 = personal_data.SellLimitOrder(trader_inst)
    open_order_2 = personal_data.BuyLimitOrder(trader_inst)
    open_order_1.update(order_type=enums.TraderOrderType.SELL_LIMIT,
                        order_id="open_order_1_id",
                        symbol="BTC/USDT",
                        current_price=decimal.Decimal("70"),
                        quantity=decimal.Decimal("10"),
                        price=decimal.Decimal("70"))
    open_order_2.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                        order_id="open_order_2_id",
                        symbol="BTC/USDT",
                        current_price=decimal.Decimal("70"),
                        quantity=decimal.Decimal("10"),
                        price=decimal.Decimal("70"),
                        reduce_only=True)
    await exchange_manager_inst.exchange_personal_data.orders_manager.upsert_order_instance(open_order_1)
    await exchange_manager_inst.exchange_personal_data.orders_manager.upsert_order_instance(open_order_2)
    assert not exchange_manager_inst.exchange_personal_data.orders_manager.pending_creation_orders
    assert exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders() == [
        open_order_1, open_order_2
    ]

    base_order = personal_data.BuyLimitOrder(trader_inst)
    base_order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                      order_id="base_order_id",
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal("55"),
                      quantity=decimal.Decimal("10"),
                      price=decimal.Decimal("70"),
                      reduce_only=False)
    base_order.has_been_bundled = True

    # simulate real trader
    trader_inst.simulate = False
    await personal_data.create_as_chained_order(base_order)
    registered_orders = exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders()
    assert len(registered_orders) == 2
    assert registered_orders[0] is open_order_1
    inserted_pending_order = exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders()[1]
    assert inserted_pending_order is base_order
    assert inserted_pending_order.reduce_only is True  # inserted_pending_order got preserved and updated
    # did not add it to orders
    assert not exchange_manager_inst.exchange_personal_data.orders_manager.pending_creation_orders

    assert base_order.is_waiting_for_chained_trigger is False
    # still not initialized
    assert base_order.is_initialized is False
    # open_order_2 got cleared
    assert open_order_2.exchange_manager is None


@pytest.mark.asyncio
async def test_create_as_active_order_using_strategy_if_any(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    inactive_order = personal_data.SellLimitOrder(trader_inst)
    group = personal_data.OneCancelsTheOtherOrderGroup(
        "plop", exchange_manager_inst.exchange_personal_data.orders_manager
    )

    with mock.patch.object(order_util, "create_as_active_order_on_exchange", mock.AsyncMock()) as create_as_active_order_on_exchange, \
        mock.patch.object(group.active_order_swap_strategy.__class__, "execute", mock.AsyncMock()) as execute_mock:
        # no strategy
        await personal_data.create_as_active_order_using_strategy_if_any(inactive_order, 123, "callback")
        create_as_active_order_on_exchange.assert_called_once_with(inactive_order, False)
        execute_mock.assert_not_called()
        create_as_active_order_on_exchange.reset_mock()

        # with strategy
        inactive_order.order_group = group
        await personal_data.create_as_active_order_using_strategy_if_any(inactive_order, 123, "callback")
        create_as_active_order_on_exchange.assert_not_called()
        execute_mock.assert_called_once_with(inactive_order, "callback", 123)


@pytest.mark.asyncio
async def test_create_as_active_order_on_exchange_with_sub_calls(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    trader_inst.simulate = False
    trader_inst.enable_inactive_orders = True
    inactive_order = personal_data.SellLimitOrder(trader_inst)
    inactive_order.is_active = False
    exchange_created_order = personal_data.SellLimitOrder(trader_inst)
    exchange_created_order.update(
        order_type=enums.TraderOrderType.SELL_LIMIT,
        order_id="base_order_id",
        symbol="BTC/USDT",
        current_price=decimal.Decimal("55"),
        quantity=decimal.Decimal("10"),
        price=decimal.Decimal("70"),
        reduce_only=False,
        fee={
            enums.FeePropertyColumns.COST.value: 1,
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
        }
    )
    await exchange_manager_inst.exchange_personal_data.orders_manager.upsert_order_instance(inactive_order)
    all_orders = exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders()
    assert all_orders == [inactive_order]
    with mock.patch.object(exchange_manager_inst.exchange, "create_order", mock.AsyncMock(return_value=exchange_created_order)) as create_order_mock, \
        mock.patch.object(order_factory, "create_order_instance_from_raw", mock.Mock(return_value=exchange_created_order)) as create_order_instance_from_raw_mock:
        active_order = await personal_data.create_as_active_order_on_exchange(inactive_order, True)
        assert active_order is exchange_created_order
        assert active_order.is_active is True
        all_orders = exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders()
        # inactive order is replaced by active_order
        assert all_orders == [active_order]
        # inactive_order is now active and cleared
        assert inactive_order.is_active is True
        assert inactive_order.exchange_manager is None
        create_order_mock.assert_called_once()
        create_order_instance_from_raw_mock.assert_called_once()


@pytest.mark.asyncio
async def test_update_order_as_inactive_on_exchange_with_sub_calls(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    trader_inst.enable_inactive_orders = True
    trader_inst.simulate = False
    active_order = personal_data.SellLimitOrder(trader_inst)
    active_order.update(
        order_type=enums.TraderOrderType.SELL_LIMIT,
        order_id="base_order_id",
        symbol="BTC/USDT",
        current_price=decimal.Decimal("55"),
        quantity=decimal.Decimal("10"),
        price=decimal.Decimal("70"),
        reduce_only=False,
        active_trigger=personal_data.create_order_price_trigger(active_order, decimal.Decimal("70"), False),
        fee={
            enums.FeePropertyColumns.COST.value: 1,
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
        }
    )
    await exchange_manager_inst.exchange_personal_data.orders_manager.upsert_order_instance(active_order)
    all_orders = exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders()
    assert all_orders == [active_order]
    assert active_order.active_trigger._trigger_event is None
    with mock.patch.object(exchange_manager_inst.exchange, "cancel_order", mock.AsyncMock(return_value=enums.OrderStatus.CANCELED)) as cancel_order_mock:
        assert await personal_data.update_order_as_inactive_on_exchange(active_order, False) is True
        assert exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders() == [active_order]
        # order is now inactive
        assert exchange_manager_inst.exchange_personal_data.orders_manager.get_all_orders(active=False) == [active_order]
        assert active_order.is_active is False
        assert active_order.status == enums.OrderStatus.OPEN
        assert active_order.active_trigger is not None
        assert active_order.active_trigger._trigger_event is not None
        cancel_order_mock.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_orders_relevancy_without_positions(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    order_mock = Mock(exchange_manager=exchange_manager_inst, symbol="BTC/USD")
    exchange_manager_inst.exchange_personal_data.positions_manager.positions = {}
    # without positions: doing nothing
    async with personal_data.ensure_orders_relevancy(order=order_mock):
        pass
    # nothing happened


@pytest.mark.asyncio
async def test_ensure_orders_relevancy_with_positions(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position = personal_data.LinearPosition(trader_inst, default_contract)
    position.symbol = DEFAULT_FUTURE_SYMBOL
    order_mock = Mock(exchange_manager=exchange_manager_inst, symbol=DEFAULT_FUTURE_SYMBOL)
    trader_mock = Mock(cancel_order=AsyncMock())
    group_mock = Mock(on_cancel=AsyncMock())
    to_cancel_order_mock = Mock(trader=trader_mock, order_group=group_mock, status=enums.OrderStatus.OPEN,
                                     is_open=Mock(return_value=True), reduce_only=True,
                                     symbol=DEFAULT_FUTURE_SYMBOL)
    # with positions
    exchange_manager_inst.exchange_personal_data.positions_manager.positions = {"BTC/USDT": position}
    exchange_manager_inst.exchange_personal_data.orders_manager.orders = {"id": to_cancel_order_mock}
    async with personal_data.ensure_orders_relevancy(order=order_mock):
        # no change
        pass
    trader_mock.cancel_order.assert_not_called()
    # with order parameter
    async with personal_data.ensure_orders_relevancy(order=order_mock):
        # changing side
        position.side = "other_side"
    trader_mock.cancel_order.assert_not_called()
    # don't canceled order as position was idle (same situation as open a short from a 0 quantity position,
    # which is considered as long)
    async with personal_data.ensure_orders_relevancy(position=position):
        # changing side
        position.side = "other_other_side"
    trader_mock.cancel_order.assert_not_called()
    # with a non-0 quantity position
    position.quantity = decimal.Decimal("2")
    # with position parameter
    async with personal_data.ensure_orders_relevancy(position=position):
        # changing side
        position.side = "other_side"
    # canceled order
    trader_mock.cancel_order.assert_called_once_with(to_cancel_order_mock)


@pytest.mark.asyncio
async def test_get_order_size_portfolio_percent(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    api.force_set_mark_price(exchange_manager_inst, "BTC/UDST", 1000)
    # no USDT in portfolio
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("0.1"), enums.TradeOrderSide.BUY, "BTC/UDST"
    ) == constants.ZERO
    # 10 BTC in portfolio
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("1"), enums.TradeOrderSide.SELL, "BTC/UDST"
    ) == decimal.Decimal("10")
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("10"), enums.TradeOrderSide.SELL, "BTC/UDST"
    ) == decimal.Decimal("100")
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("11"), enums.TradeOrderSide.SELL, "BTC/UDST"
    ) == decimal.Decimal("100")
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("6.6666"), enums.TradeOrderSide.SELL, "BTC/UDST"
    ) == decimal.Decimal("66.666")

    # 100 USDT in portfolio
    exchange_manager_inst.exchange_personal_data.portfolio_manager.portfolio.portfolio['UDST'].available \
        = decimal.Decimal("100")
    exchange_manager_inst.exchange_personal_data.portfolio_manager.portfolio.portfolio['UDST'].total \
        = decimal.Decimal("100")
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("0.1"), enums.TradeOrderSide.BUY, "BTC/UDST"
    ) == decimal.Decimal("100")
    assert await personal_data.get_order_size_portfolio_percent(
        exchange_manager_inst, decimal.Decimal("0.01"), enums.TradeOrderSide.BUY, "BTC/UDST"
    ) == decimal.Decimal("10")


def test_get_valid_split_orders():
    # example SOL/BTC values from 12/09/2023
    symbol_market = {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.01,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 90000000.0,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.0001,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 9000000.0
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 1e-07,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000.0
            },
        },
        enums.ExchangeConstantsMarketStatusColumns.PRECISION.value: {
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 7,
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 2
        }
    }
    # all valid values
    prices = [
        decimal.Decimal("0.0006858"),
        decimal.Decimal("0.0006908"),
        decimal.Decimal("0.0006938"),
        decimal.Decimal("0.0006958"),
    ]
    assert personal_data.get_valid_split_orders(
        decimal.Decimal("1"),
        prices,
        symbol_market
    ) == ([decimal.Decimal("1") / len(prices)] * len(prices), prices)

    # too small amount for cost: adapt to 3 orders
    assert personal_data.get_valid_split_orders(
        decimal.Decimal("0.5"),
        prices,
        symbol_market
    ) == ([decimal.Decimal("0.5") / 3] * 3, prices[:3])

    # too small amount for cost: adapt to 1 orders
    assert personal_data.get_valid_split_orders(
        decimal.Decimal("0.1"),
        prices,
        symbol_market
    ) == ([decimal.Decimal('0.1')], [decimal.Decimal('0.0006858')])

    # too small amount for cost (because of the lowest price order amount that gets truncated because of
    # exchange precision rules): adapt to 0 orders

    prices = [
        decimal.Decimal("0.0006963"),
        decimal.Decimal("0.0006908"),
        decimal.Decimal("0.0006938"),
        decimal.Decimal("0.0006958"),
    ]
    assert personal_data.get_valid_split_orders(
        decimal.Decimal("0.14985"),
        prices,
        symbol_market,
    ) == ([decimal.Decimal('0.14985')], [decimal.Decimal('0.0006963')])


def test_get_valid_split_orders_with_amount_ratio_per_order():
    # example SOL/BTC values from 12/09/2023
    symbol_market = {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.01,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 90000000.0,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.0001,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 9000000.0
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 1e-07,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000.0
            },
        },
        enums.ExchangeConstantsMarketStatusColumns.PRECISION.value: {
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 7,
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 2
        }
    }

    # all valid values
    input_prices = [
        decimal.Decimal("0.0006858"),
        decimal.Decimal("0.0006908"),
        decimal.Decimal("0.0006938"),
        decimal.Decimal("0.0006958"),
    ]
    amount_ratio_per_order = [
        decimal.Decimal("0.12"),
        decimal.Decimal("0.24"),
        decimal.Decimal("0.36"),
        decimal.Decimal("0.28"),
    ]
    # invalid inputs
    with pytest.raises(ValueError):
        personal_data.get_valid_split_orders(
            decimal.Decimal("2"),
            input_prices,
            symbol_market,
            amount_ratio_per_order=[1, 2, 3]    # not enough values
        )
    with pytest.raises(ValueError):
        personal_data.get_valid_split_orders(
            decimal.Decimal("2"),
            [decimal.Decimal("0.5")],
            symbol_market,
            amount_ratio_per_order=[decimal.Decimal(0)]    # 0 values
        )
    with pytest.raises(ValueError):
        personal_data.get_valid_split_orders(
            decimal.Decimal("2"),
            [decimal.Decimal("0.5")],
            symbol_market,
            amount_ratio_per_order=[decimal.Decimal(-1.2)]    # negative values
        )

    # valid inputs
    volumes, prices = personal_data.get_valid_split_orders(
        decimal.Decimal("2"),
        input_prices,
        symbol_market,
        amount_ratio_per_order=amount_ratio_per_order
    )
    assert (volumes, prices) == (
        [decimal.Decimal("2") * amount_ratio for amount_ratio in amount_ratio_per_order],
        prices
    )
    assert sum(volumes) == decimal.Decimal("2")

    # too small amount for cost: adapt to 2 orders
    amount_ratio_per_order = [decimal.Decimal(33), decimal.Decimal(44), decimal.Decimal(55), decimal.Decimal(66)]
    total_ratio = sum(amount_ratio_per_order[:2])
    volumes, prices = personal_data.get_valid_split_orders(
        decimal.Decimal("0.5"),
        input_prices,
        symbol_market,
        amount_ratio_per_order=amount_ratio_per_order
    )
    assert (volumes, prices) == (
        [decimal.Decimal("0.5") * amount_ratio/total_ratio for amount_ratio in amount_ratio_per_order[:2]],
        prices
    )
    assert sum(volumes) == decimal.Decimal("0.5")

    # too small amount for cost: adapt to 1 order
    volumes, prices = personal_data.get_valid_split_orders(
        decimal.Decimal("0.1"),
        input_prices,
        symbol_market,
        amount_ratio_per_order=amount_ratio_per_order
    )
    assert (volumes, prices) == ([decimal.Decimal('0.1')], [decimal.Decimal('0.0006858')])

    # too small amount for cost (because of the lowest price order amount that gets truncated because of
    # exchange precision rules): adapt to 0 orders

    input_prices = [
        decimal.Decimal("0.0006963"),
        decimal.Decimal("0.0006908"),
        decimal.Decimal("0.0006938"),
        decimal.Decimal("0.0006958"),
    ]
    assert personal_data.get_valid_split_orders(
        decimal.Decimal("0.14985"),
        input_prices,
        symbol_market,
        amount_ratio_per_order=amount_ratio_per_order
    ) == ([decimal.Decimal('0.14985')], [decimal.Decimal('0.0006963')])


def test_get_split_orders_count_and_increment():
    # example SOL/BTC values from 12/09/2023
    symbol_market = {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.01,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 90000000.0,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.0001,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 9000000.0
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 1e-07,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000.0
            },
        },
        enums.ExchangeConstantsMarketStatusColumns.PRECISION.value: {
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 7,
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 2
        }
    }
    # all valid values
    assert personal_data.get_split_orders_count_and_increment(
        decimal.Decimal("0.0006858"),
        decimal.Decimal("0.0006958"),
        decimal.Decimal("1"),
        4,
        symbol_market,
        True
    ) == (4, decimal.Decimal('0.0000025'))

    # too small amount for cost: adapt to 3 orders
    assert personal_data.get_split_orders_count_and_increment(
        decimal.Decimal("0.0006858"),
        decimal.Decimal("0.0006958"),
        decimal.Decimal("0.5"),
        4,
        symbol_market,
        True
    ) == (3, decimal.Decimal('0.000003333333333333333333333333333'))

    # too small amount for cost: adapt to 0 orders
    assert personal_data.get_split_orders_count_and_increment(
        decimal.Decimal("0.0006858"),
        decimal.Decimal("0.0006958"),
        decimal.Decimal("0.1"),
        4,
        symbol_market,
        True
    ) == (0, decimal.Decimal('0'))

    # too small amount for cost (because of the lowest price order amount that gets truncated because of
    # exchange precision rules): adapt to 0 orders
    assert personal_data.get_split_orders_count_and_increment(
        decimal.Decimal("0.0006963"),
        decimal.Decimal("0.0006958"),
        decimal.Decimal("0.14985"),
        4,
        symbol_market,
        False
    ) == (0, decimal.Decimal('0'))


def test_ensure_orders_limit():
    symbol = "BTC/USDT"
    exchange_manager = mock.Mock(
        exchange = mock.Mock(
            get_max_orders_count = mock.Mock(return_value=5),
        ),
        exchange_personal_data = mock.Mock(
            orders_manager = mock.Mock(
                get_open_orders = mock.Mock(
                    return_value=[
                        mock.Mock(order_type=enums.TraderOrderType.BUY_LIMIT),
                        mock.Mock(order_type=enums.TraderOrderType.SELL_LIMIT),
                        mock.Mock(order_type=enums.TraderOrderType.STOP_LOSS),
                        mock.Mock(order_type=enums.TraderOrderType.STOP_LOSS),
                        mock.Mock(order_type=enums.TraderOrderType.STOP_LOSS),
                    ],
                )
            )
        )
    )

    # do not raise
    order_util.ensure_orders_limit(exchange_manager, symbol, [])
    assert exchange_manager.exchange.get_max_orders_count.call_count == 2
    assert exchange_manager.exchange.get_max_orders_count.mock_calls[0].args == (
        symbol, enums.TraderOrderType.SELL_LIMIT
    )
    assert exchange_manager.exchange.get_max_orders_count.mock_calls[1].args == (
        symbol, enums.TraderOrderType.STOP_LOSS
    )
    exchange_manager.exchange_personal_data.orders_manager.get_open_orders.assert_called_once_with(
        symbol=symbol, active=None
    )

    # ok added limit orders
    order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.BUY_LIMIT]*2)
    order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.BUY_LIMIT]*3)
    # too many added limit orders
    with pytest.raises(octobot_trading.errors.MaxOpenOrderReachedForSymbolError):
        order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.BUY_LIMIT]*4)
    with pytest.raises(octobot_trading.errors.MaxOpenOrderReachedForSymbolError):
        order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.BUY_LIMIT]*10)

    # ok added stop orders
    order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.STOP_LOSS])
    order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.STOP_LOSS_LIMIT]*2)
    # too many added stop orders
    with pytest.raises(octobot_trading.errors.MaxOpenOrderReachedForSymbolError):
        order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.STOP_LOSS]*3)
    with pytest.raises(octobot_trading.errors.MaxOpenOrderReachedForSymbolError):
        order_util.ensure_orders_limit(exchange_manager, symbol, [enums.TraderOrderType.STOP_LOSS_LIMIT]*10)
