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
import decimal
import pytest
import mock

import octobot_trading.api as trading_api
import octobot_commons.signals as commons_signals
import octobot_trading.enums as trading_enums
import octobot_trading.errors as errors
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data
import octobot_services.api as services_api
import octobot_trading.modes.script_keywords as script_keywords

from tentacles.Trading.Mode.remote_trading_signals_trading_mode.tests import local_trader, mocked_sell_limit_signal, \
    mocked_bundle_stop_loss_in_sell_limit_in_market_signal, mocked_buy_market_signal, mocked_buy_limit_signal, \
    mocked_update_leverage_signal, mocked_bundle_trigger_above_stop_loss_in_sell_limit_in_market_signal, \
    mocked_bundle_trailing_stop_loss_in_sell_limit_in_market_signal, mocked_sell_limit_signal_with_trailing_group


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_internal_callback(local_trader, mocked_sell_limit_signal, mocked_update_leverage_signal):
    _, consumer, _ = local_trader
    consumer.logger = mock.Mock(info=mock.Mock(), error=mock.Mock(), exception=mock.Mock())
    with mock.patch.object(consumer, "_handle_signal_orders", new=mock.AsyncMock()) \
         as _handle_signal_orders_mock:
        await consumer.internal_callback(
            "trading_mode_name", "cryptocurrency", "symbol", "time_frame", "final_note", "state", mocked_sell_limit_signal
        )
        _handle_signal_orders_mock.assert_called_once_with("symbol", mocked_sell_limit_signal)
        consumer.logger.info.assert_not_called()
        consumer.logger.error.assert_not_called()
        consumer.logger.exception.assert_not_called()

    with mock.patch.object(consumer, "_handle_positions_signal", new=mock.AsyncMock()) \
         as _handle_positions_signal_mock:
        await consumer.internal_callback("trading_mode_name", "cryptocurrency", "symbol", "time_frame", "final_note",
                                         "state", mocked_update_leverage_signal)
        _handle_positions_signal_mock.assert_called_once_with("symbol", mocked_update_leverage_signal)
        consumer.logger.info.assert_not_called()
        consumer.logger.error.assert_not_called()
        consumer.logger.exception.assert_not_called()

    with mock.patch.object(consumer, "_handle_signal_orders",
                           new=mock.AsyncMock(side_effect=errors.MissingMinimalExchangeTradeVolume)) \
         as _handle_signal_orders_mock:
        await consumer.internal_callback("trading_mode_name", "cryptocurrency", "symbol/x", "time_frame", "final_note",
                                         "state", mocked_sell_limit_signal)
        _handle_signal_orders_mock.assert_called_once_with("symbol/x", mocked_sell_limit_signal)
        consumer.logger.info.assert_called_once()
        consumer.logger.error.assert_not_called()
        consumer.logger.exception.assert_not_called()
        consumer.logger.info.reset_mock()

    with mock.patch.object(consumer, "_handle_signal_orders",
                           new=mock.AsyncMock(side_effect=RuntimeError)) \
         as _handle_signal_orders_mock:
        await consumer.internal_callback("trading_mode_name", "cryptocurrency", "symbol/x", "time_frame", "final_note",
                                         "state", mocked_sell_limit_signal)
        _handle_signal_orders_mock.assert_called_once_with("symbol/x", mocked_sell_limit_signal)
        consumer.logger.info.assert_not_called()
        consumer.logger.error.assert_not_called()
        consumer.logger.exception.assert_called_once()

    with mock.patch.object(consumer, "_handle_signal_orders",
                           new=mock.AsyncMock(side_effect=RuntimeError)) as _handle_signal_orders_mock, \
        mock.patch.object(consumer, "_handle_positions_signal",
            new=mock.AsyncMock(side_effect=RuntimeError)) \
         as _handle_positions_signal_mock:
        mocked_sell_limit_signal.topic = "plop"
        await consumer.internal_callback("trading_mode_name", "cryptocurrency", "symbol/x", "time_frame", "final_note",
                                         "state", mocked_sell_limit_signal)
        _handle_signal_orders_mock.assert_not_called()
        _handle_positions_signal_mock.assert_not_called()
        consumer.logger.info.assert_not_called()
        consumer.logger.error.assert_called_once()
        consumer.logger.exception.assert_called_once()


async def test_handle_signal_orders(local_trader, mocked_bundle_stop_loss_in_sell_limit_in_market_signal):
    _, consumer, trader = local_trader
    symbol = mocked_bundle_stop_loss_in_sell_limit_in_market_signal.content[
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value
    ]
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    assert consumer.trading_mode.last_signal_description == ""
    await consumer._handle_signal_orders(symbol, mocked_bundle_stop_loss_in_sell_limit_in_market_signal)
    # ensure orders are created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    # market order is filled, chained & bundled orders got created
    assert isinstance(orders[0], trading_personal_data.StopLossOrder)
    assert isinstance(orders[0].order_group, trading_personal_data.BalancedTakeProfitAndStopOrderGroup)
    assert isinstance(orders[0].order_group.active_order_swap_strategy, trading_personal_data.StopFirstActiveOrderSwapStrategy)
    assert orders[0].order_group.active_order_swap_strategy.swap_timeout == 3
    assert orders[0].order_group.active_order_swap_strategy.trigger_price_configuration == trading_enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value
    assert orders[0].trailing_profile is None
    assert orders[0].update_with_triggering_order_fees is False
    assert orders[0].origin_price == decimal.Decimal("9990")
    assert orders[0].trigger_above is False
    assert orders[0].is_active is True
    assert orders[0].active_trigger is None
    assert isinstance(orders[0].cancel_policy, trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy)
    assert isinstance(orders[1], trading_personal_data.SellLimitOrder)
    assert orders[1].order_group is orders[0].order_group
    assert orders[1].trailing_profile is None
    assert orders[1].is_active is False
    assert orders[1].active_trigger.trigger_price == decimal.Decimal(21)
    assert orders[1].active_trigger.trigger_above is False
    assert orders[1].update_with_triggering_order_fees is True
    assert orders[1].trigger_above is True
    assert orders[1].origin_quantity == decimal.Decimal("0.10713784")   # initial quantity as
    assert orders[1].cancel_policy is None
    # update_with_triggering_order_fees is False
    trades = list(exchange_manager.exchange_personal_data.trades_manager.trades.values())
    assert len(trades) == 1
    assert trades[0].trade_type, trading_enums.TraderOrderType.BUY_MARKET
    assert trades[0].status is trading_enums.OrderStatus.FILLED
    assert "2" in consumer.trading_mode.last_signal_description

    # disable created order group so that changing their groups doesnt cancel them
    await orders[0].order_group.enable(False)
    # now edit, cancel orders and create a new one
    # change StopLossOrder group and cancel SellLimitOrder
    nested_edit_signal, cancel_signal, create_signal = _group_edit_cancel_create_order_signals(
        orders[0].order_id, "new_group_id", trading_personal_data.OneCancelsTheOtherOrderGroup.__name__,
        orders[0].order_id, "3.356892%", 2000,
        orders[1].order_id
    )
    await consumer._handle_signal_orders(symbol, nested_edit_signal)
    await consumer._handle_signal_orders(symbol, cancel_signal)
    await consumer._handle_signal_orders(symbol, create_signal)
    # ensure orders are created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    # market order is filled, chained & bundled orders got created
    assert isinstance(orders[0], trading_personal_data.StopLossOrder)
    assert isinstance(orders[0].order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)    # not balance group anymore
    assert orders[0].order_group.name == "new_group_id"
    assert orders[0].origin_quantity == decimal.Decimal("0.3392821050783528672")    # changed quantity according to fees
    assert orders[0].origin_price == decimal.Decimal("2000")    # changed price
    assert isinstance(orders[1], trading_personal_data.BuyLimitOrder)   # not sell order (sell is cancelled)
    trades = list(exchange_manager.exchange_personal_data.trades_manager.trades.values())
    assert len(trades) == 2
    assert trades[0].trade_type, trading_enums.TraderOrderType.BUY_MARKET
    assert trades[1].trade_type, trading_enums.TraderOrderType.SellLimitOrder
    assert trades[1].status is trading_enums.OrderStatus.CANCELED
    assert "1" in consumer.trading_mode.last_signal_description


async def test_handle_signal_orders_trailing_stop_with_cancel_policy(
    local_trader, mocked_bundle_trailing_stop_loss_in_sell_limit_in_market_signal
):
    _, consumer, trader = local_trader
    symbol = mocked_bundle_trailing_stop_loss_in_sell_limit_in_market_signal.content[
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value
    ]
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    assert consumer.trading_mode.last_signal_description == ""
    await consumer._handle_signal_orders(symbol, mocked_bundle_trailing_stop_loss_in_sell_limit_in_market_signal)
    # ensure orders are created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    # market order is filled, chained & bundled orders got created
    assert isinstance(orders[0], trading_personal_data.StopLossOrder)
    assert isinstance(orders[0].order_group, trading_personal_data.TrailingOnFilledTPBalancedOrderGroup)
    # trailing profile is restored
    assert orders[0].trailing_profile == trading_personal_data.FilledTakeProfitTrailingProfile([
        trading_personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    assert orders[0].update_with_triggering_order_fees is False
    assert orders[0].origin_price == decimal.Decimal("9990")
    assert orders[0].trigger_above is False
    assert isinstance(orders[0].cancel_policy, trading_personal_data.ExpirationTimeOrderCancelPolicy)
    assert orders[0].cancel_policy.expiration_time == 1000.0
    assert isinstance(orders[1], trading_personal_data.SellLimitOrder)
    assert orders[1].order_group is orders[0].order_group
    assert orders[1].trailing_profile is None
    assert orders[1].update_with_triggering_order_fees is True
    assert orders[1].trigger_above is True
    assert orders[1].origin_quantity == decimal.Decimal("0.10713784")   # initial quantity as
    assert orders[1].cancel_policy is None
    # update_with_triggering_order_fees is False
    trades = list(exchange_manager.exchange_personal_data.trades_manager.trades.values())
    assert len(trades) == 1
    assert trades[0].trade_type, trading_enums.TraderOrderType.BUY_MARKET
    assert trades[0].status is trading_enums.OrderStatus.FILLED
    assert "2" in consumer.trading_mode.last_signal_description


async def test_handle_signal_orders_trigger_above_stop_loss(local_trader, mocked_bundle_trigger_above_stop_loss_in_sell_limit_in_market_signal):
    _, consumer, trader = local_trader
    symbol = mocked_bundle_trigger_above_stop_loss_in_sell_limit_in_market_signal.content[
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value
    ]
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    assert consumer.trading_mode.last_signal_description == ""
    await consumer._handle_signal_orders(symbol, mocked_bundle_trigger_above_stop_loss_in_sell_limit_in_market_signal)
    # ensure orders are created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    # market order is filled, chained & bundled orders got created
    assert isinstance(orders[0], trading_personal_data.StopLossOrder)
    assert isinstance(orders[0].order_group, trading_personal_data.BalancedTakeProfitAndStopOrderGroup)
    assert orders[0].update_with_triggering_order_fees is False
    assert orders[0].origin_price == decimal.Decimal("999999990")
    assert orders[0].trigger_above is True
    assert isinstance(orders[1], trading_personal_data.SellLimitOrder)
    assert orders[1].order_group is orders[0].order_group
    assert orders[1].update_with_triggering_order_fees is True
    assert orders[1].trigger_above is True
    assert orders[1].origin_quantity == decimal.Decimal("0.10713784")   # initial quantity as
    # update_with_triggering_order_fees is False
    trades = list(exchange_manager.exchange_personal_data.trades_manager.trades.values())
    assert len(trades) == 1
    assert trades[0].trade_type, trading_enums.TraderOrderType.BUY_MARKET
    assert trades[0].status is trading_enums.OrderStatus.FILLED
    assert "2" in consumer.trading_mode.last_signal_description


async def test_handle_signal_orders_no_triggering_order(
    local_trader, mocked_bundle_stop_loss_in_sell_limit_in_market_signal
):
    _, consumer, trader = local_trader
    symbol = mocked_bundle_stop_loss_in_sell_limit_in_market_signal.content[
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value
    ]
    exchange_manager = trader.exchange_manager
    await consumer._handle_signal_orders(symbol, mocked_bundle_stop_loss_in_sell_limit_in_market_signal)
    # ensure orders are created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    # market order is filled, chained & bundled orders got created
    # same as test_handle_signal_orders: skip other asserts
    assert orders[1].order_group is orders[0].order_group
    assert orders[0].order_id in exchange_manager.exchange_personal_data.orders_manager.\
        get_all_active_and_pending_orders_id()
    assert orders[1].order_id in exchange_manager.exchange_personal_data.orders_manager.\
        get_all_active_and_pending_orders_id()

    # now edit, cancel orders and create a new one
    # change StopLossOrder group and cancel SellLimitOrder
    _, cancel_signal, _ = _group_edit_cancel_create_order_signals(
        orders[0].order_id, "new_group_id", trading_personal_data.OneCancelsTheOtherOrderGroup.__name__,
        orders[0].order_id, "3.356892%", 2000,
        orders[1].order_id
    )
    cancel_signal.content[trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value] = "0"
    await consumer._handle_signal_orders(symbol, cancel_signal)

    port_cancel_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    # order 1 got cancelled, since it's grouped with order 0, both are cancelled
    assert len(port_cancel_orders) ==0
    assert orders[0].order_id not in exchange_manager.exchange_personal_data.orders_manager.\
        get_all_active_and_pending_orders_id()
    assert orders[1].order_id not in exchange_manager.exchange_personal_data.orders_manager.\
        get_all_active_and_pending_orders_id()


async def test_handle_signal_orders_reduce_quantity_create_order(local_trader, mocked_buy_market_signal):
    _, consumer, trader = local_trader
    symbol = mocked_buy_market_signal.content[
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value
    ]
    mocked_buy_market_signal.content[trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value] = "75%"
    mocked_buy_market_signal.content[trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value] = None
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    assert consumer.trading_mode.last_signal_description == ""
    await consumer._handle_signal_orders(symbol, mocked_buy_market_signal)
    # market order is filled, chained & bundled orders got created
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 0
    trades = list(exchange_manager.exchange_personal_data.trades_manager.trades.values())
    assert len(trades) == 1
    assert trades[0].trade_type, trading_enums.TraderOrderType.BUY_MARKET
    # used 75% of funds
    # can buy max 2, should buy 1.5, buy one because of config
    assert trades[0].origin_quantity == decimal.Decimal("1")
    assert trades[0].origin_price == decimal.Decimal("1000")


async def test_handle_signal_orders_reduce_quantity_edit_order(local_trader, mocked_buy_limit_signal):
    _, consumer, trader = local_trader
    symbol = mocked_buy_limit_signal.content[trading_enums.TradingSignalOrdersAttrs.SYMBOL.value]
    trading_api.force_set_mark_price(trader.exchange_manager, "BTC/USDT:USDT", 1000)
    edit_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.EDIT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: None,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: symbol,
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: 0,
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: "80%",
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: None,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: mocked_buy_limit_signal.content[
                trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value
            ],
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        },
    )
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    assert consumer.trading_mode.last_signal_description == ""
    await consumer._handle_signal_orders(symbol, mocked_buy_limit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 1
    assert orders[0].origin_quantity == decimal.Decimal("0.10714817")
    await consumer._handle_signal_orders(symbol, edit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 1
    assert orders[0].origin_quantity == decimal.Decimal("1")    # use 50% max as quantity (vs 80% in signal)


async def test_handle_signal_create_orders_not_enough_funds_using_min_amount(local_trader, mocked_buy_limit_signal):
    _, consumer, trader = local_trader
    symbol = mocked_buy_limit_signal.content[trading_enums.TradingSignalOrdersAttrs.SYMBOL.value]
    trading_api.force_set_mark_price(trader.exchange_manager, "BTC/USDT:USDT", 1000)
    # too small amount for the current porfolio to handle within exchange rules
    amount = "0.00000001%"
    limit_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: symbol,
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.SELL_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: amount,
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 20898.03,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 20600.31,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "98ea73a0-ed38-4fca-9744-ed7f80a2d3ef",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.OneCancelsTheOtherOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "12e7ad8f-10a1-4cd3-bf86-d972226bd079",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        },
    )
    consumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = True
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    await consumer._handle_signal_orders(symbol, limit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 1
    order_1 = orders[0]
    assert order_1.origin_quantity == decimal.Decimal("0.00001")    # minimal amount according to exchange rules

    consumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = False
    # now disable minimal amount config
    await consumer._handle_signal_orders(symbol, limit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 1
    assert orders[0] is order_1  # no order created

    consumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = True
    # re-enable minimal amount config
    # same order id: no order created
    await consumer._handle_signal_orders(symbol, limit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 1
    assert orders[0] is order_1  # no order created
    # change order id not to skip creation
    limit_signal.content[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value] = "123"
    await consumer._handle_signal_orders(symbol, limit_signal)
    orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
    assert len(orders) == 2
    assert orders[0] is order_1  # no order created
    assert orders[1].origin_quantity == decimal.Decimal("0.00001")    # minimal amount according to exchange rules


async def test_handle_signal_create_orders_not_enough_available_funds_even_for_min_order(local_trader, mocked_buy_limit_signal):
    _, consumer, trader = local_trader
    symbol = "BTC/USDT:USDT"
    trading_api.force_set_mark_price(trader.exchange_manager, "BTC/USDT:USDT", 1000)
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["BTC"].available = trading_constants.ZERO
    limit_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: symbol,
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.SELL_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "39.5865%a",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 20898.03,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 20600.31,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "98ea73a0-ed38-4fca-9744-ed7f80a2d3ef",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.OneCancelsTheOtherOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "12e7ad8f-10a1-4cd3-bf86-d972226bd079",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        },
    )
    consumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = True
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    await consumer._handle_signal_orders(symbol, limit_signal)
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []


async def test_handle_signal_create_orders_not_enough_total_funds_even_for_min_order(local_trader, mocked_buy_limit_signal):
    _, consumer, trader = local_trader
    symbol = "BTC/USDT:USDT"
    trading_api.force_set_mark_price(trader.exchange_manager, "BTC/USDT:USDT", 1000)
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["BTC"].total = trading_constants.ZERO
    limit_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: symbol,
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.SELL_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "39.5865%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 20898.03,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 20600.31,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "98ea73a0-ed38-4fca-9744-ed7f80a2d3ef",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.OneCancelsTheOtherOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "12e7ad8f-10a1-4cd3-bf86-d972226bd079",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        },
    )
    consumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = True
    exchange_manager = trader.exchange_manager
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []
    await consumer._handle_signal_orders(symbol, limit_signal)
    assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []


async def test_send_alert_notification(local_trader):
    _, consumer, _ = local_trader
    with mock.patch.object(services_api, "send_notification", mock.AsyncMock()) as send_notification_mock:
        await consumer._send_alert_notification("BTC/USDT:USDT", 42, 62, 78)
        send_notification_mock.assert_called_once()
        notification = send_notification_mock.mock_calls[0].args[0]
        assert all(str(counter) in notification.text for counter in (42, 62, 78))

        send_notification_mock.reset_mock()
        await consumer._send_alert_notification("BTC/USDT:USDT", 0, 0, 99)
        send_notification_mock.assert_called_once()
        notification = send_notification_mock.mock_calls[0].args[0]
        assert "99" in notification.text
        assert "0" not in notification.text


# TODO add more unit hedge case tests when arch is validated


def _group_edit_cancel_create_order_signals(to_group_id, group_id, group_type,
                                            to_edit_id, to_edit_target_amount, to_edit_price,
                                            to_cancel_id):
    nested_edit_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value:
                trading_enums.TradingSignalOrdersActions.ADD_TO_GROUP.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.BUY_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.3574085830652285%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 800.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: group_id,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: group_type,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "second wave order",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: to_group_id,
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [
                {
                    trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.EDIT.value,
                    trading_enums.TradingSignalOrdersAttrs.SIDE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
                    trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
                    trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
                    trading_enums.TradingSignalOrdersAttrs.TYPE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: 0,
                    trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
                    trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: to_edit_target_amount,
                    trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
                    trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: to_edit_price,
                    trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: None,
                    trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: None,
                    trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
                    trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
                    trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
                    trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: to_edit_id,
                    trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
                    trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
                    trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
                },
            ],
        },
    )
    cancel_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CANCEL.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: None,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: 0,
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: None,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: None,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: None,
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: to_cancel_id,
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        },
    )
    create_signal = commons_signals.Signal(
        "moonmoon",
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.BUY_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.3574085830652285%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 800.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "second wave order",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "aaaa-f970-45d9-9ba8-f63da17f17ba",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        }
    )
    return nested_edit_signal, cancel_signal, create_signal


async def test_handle_positions_signal(local_trader, mocked_update_leverage_signal):
    _, consumer, trader = local_trader
    symbol = mocked_update_leverage_signal.content[
        trading_enums.TradingSignalPositionsAttrs.SYMBOL.value
    ]
    with mock.patch.object(consumer, "_edit_position", mock.AsyncMock()) as _edit_position_mock:
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        _edit_position_mock.assert_called_once_with(symbol, mocked_update_leverage_signal)
        _edit_position_mock.reset_mock()

        # unknown action
        mocked_update_leverage_signal.content[trading_enums.TradingSignalCommonsAttrs.ACTION.value] = "plop"
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        _edit_position_mock.assert_not_called()


async def test_edit_position(local_trader, mocked_update_leverage_signal):
    _, consumer, trader = local_trader
    trader.exchange_manager.is_future = False
    symbol = mocked_update_leverage_signal.content[
        trading_enums.TradingSignalPositionsAttrs.SYMBOL.value
    ]
    with mock.patch.object(trader, "set_leverage", mock.AsyncMock()) as set_leverage_mock:
        leverage = mocked_update_leverage_signal.content[
            trading_enums.TradingSignalPositionsAttrs.LEVERAGE.value
        ]
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        set_leverage_mock.assert_not_called()

        trader.exchange_manager.is_future = True
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        set_leverage_mock.assert_called_once_with(symbol, None, decimal.Decimal(str(leverage)))
        set_leverage_mock.reset_mock()

        mocked_update_leverage_signal.content[
            trading_enums.TradingSignalPositionsAttrs.SIDE.value
        ] = trading_enums.PositionSide.LONG.value
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        set_leverage_mock.assert_called_once_with(symbol, trading_enums.PositionSide.LONG, decimal.Decimal(str(leverage)))

    # do not propagate errors
    with mock.patch.object(trader, "set_leverage", mock.AsyncMock(side_effect=NotImplementedError)) as set_leverage_mock:
        await consumer._handle_positions_signal(symbol, mocked_update_leverage_signal)
        set_leverage_mock.assert_called_once()