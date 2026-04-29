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
import pytest
import mock

import octobot_commons.signals as commons_signals
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.signals as signals
import octobot_trading.signals.util as signals_util

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import buy_limit_order, sell_limit_order, buy_market_order

import octobot_trading.personal_data as personal_data


@pytest.mark.asyncio
async def test_create_order_signal_description(buy_limit_order, sell_limit_order, buy_market_order):
    buy_market_order.reduce_only = True
    buy_market_order.tag = "hello"
    buy_market_order.symbol = "BTC/ETH"
    buy_market_order.origin_quantity = decimal.Decimal("1.12")
    exchange_manager = buy_market_order.exchange_manager
    assert signals.create_order_signal_content(buy_market_order, enums.TradingSignalOrdersActions.CREATE,
                                               "strat", exchange_manager) == {
        enums.TradingSignalCommonsAttrs.ACTION.value: enums.TradingSignalOrdersActions.CREATE.value,
        enums.TradingSignalOrdersAttrs.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.TradingSignalOrdersAttrs.STRATEGY.value: "strat",
        enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/ETH",
        enums.TradingSignalOrdersAttrs.EXCHANGE.value: "binanceus",
        enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: enums.ExchangeTypes.SPOT.value,
        enums.TradingSignalOrdersAttrs.TYPE.value: enums.TraderOrderType.BUY_MARKET.value,
        enums.TradingSignalOrdersAttrs.QUANTITY.value: float(buy_market_order.origin_quantity),
        enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: None,
        enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
        enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: None,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
        enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
        enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
        enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
        enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: None,
        enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: True,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: None,
        enums.TradingSignalOrdersAttrs.TAG.value: "hello",
        enums.TradingSignalOrdersAttrs.ORDER_ID.value: buy_market_order.order_id,
        enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
        enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
        enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
        enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: None,
    }


    buy_limit_order.reduce_only = True
    buy_limit_order.tag = "hello"
    buy_limit_order.symbol = "BTC/ETH"
    buy_limit_order.origin_price = decimal.Decimal("1.11")
    buy_limit_order.origin_quantity = decimal.Decimal("1.12")
    buy_limit_order.origin_stop_price = decimal.Decimal("1.13")
    buy_limit_order.is_active = False
    buy_limit_order.use_active_trigger(personal_data.create_order_price_trigger(buy_limit_order, decimal.Decimal("1.14"), False))
    buy_limit_order.cancel_policy = personal_data.create_cancel_policy(
        personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        {
            "expiration_time": 999
        }
    )
    exchange_manager = buy_limit_order.exchange_manager
    assert signals.create_order_signal_content(buy_limit_order, enums.TradingSignalOrdersActions.CREATE,
                                               "strat", exchange_manager) == {
        enums.TradingSignalCommonsAttrs.ACTION.value: enums.TradingSignalOrdersActions.CREATE.value,
        enums.TradingSignalOrdersAttrs.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.TradingSignalOrdersAttrs.STRATEGY.value: "strat",
        enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/ETH",
        enums.TradingSignalOrdersAttrs.EXCHANGE.value: "binanceus",
        enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: enums.ExchangeTypes.SPOT.value,
        enums.TradingSignalOrdersAttrs.TYPE.value: enums.TraderOrderType.BUY_LIMIT.value,
        enums.TradingSignalOrdersAttrs.QUANTITY.value: float(buy_limit_order.origin_quantity),
        enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: None,
        enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
        enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: False,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
        enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: float(buy_limit_order.origin_price),
        enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.STOP_PRICE.value: float(buy_limit_order.origin_stop_price),
        enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: float(buy_limit_order.created_last_price),
        enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
        enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
        enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
        enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: None,
        enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: False,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value: 1.14,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: False,
        enums.TradingSignalOrdersAttrs.TAG.value: "hello",
        enums.TradingSignalOrdersAttrs.ORDER_ID.value: buy_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
        enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
        enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
        enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: {
            "expiration_time": 999
        },
    }

    sell_limit_order.add_chained_order(buy_limit_order)
    sell_limit_order.symbol = "BTC/ETH"
    sell_limit_order.is_active = False
    sell_limit_order.use_active_trigger(personal_data.create_order_price_trigger(sell_limit_order, decimal.Decimal("2.14"), True))
    buy_limit_order.associate_to_entry("1")
    buy_limit_order.use_active_trigger(personal_data.create_order_price_trigger(buy_limit_order, decimal.Decimal("1.14"), True))
    buy_limit_order.cancel_policy = personal_data.create_cancel_policy(
        personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
        {}
    )
    await buy_limit_order.set_as_chained_order(sell_limit_order, True, {}, True)
    assert signals.create_order_signal_content(
        buy_limit_order,
        enums.TradingSignalOrdersActions.CREATE,
        "strat",
        exchange_manager,
        target_amount="1%",
        target_position="2",
    ) == {
        enums.TradingSignalCommonsAttrs.ACTION.value: enums.TradingSignalOrdersActions.CREATE.value,
        enums.TradingSignalOrdersAttrs.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.TradingSignalOrdersAttrs.STRATEGY.value: "strat",
        enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/ETH",
        enums.TradingSignalOrdersAttrs.EXCHANGE.value: "binanceus",
        enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: enums.ExchangeTypes.SPOT.value,
        enums.TradingSignalOrdersAttrs.TYPE.value: enums.TraderOrderType.BUY_LIMIT.value,
        enums.TradingSignalOrdersAttrs.QUANTITY.value: float(buy_limit_order.origin_quantity),
        enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "1%",
        enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: "2",
        enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: False,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
        enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: float(buy_limit_order.origin_price),
        enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.STOP_PRICE.value: float(buy_limit_order.origin_stop_price),
        enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: float(buy_limit_order.created_last_price),
        enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
        enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
        enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
        enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
        enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: None,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value: None,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: None,
        enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: False,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value: 1.14,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: True,
        enums.TradingSignalOrdersAttrs.TAG.value: "hello",
        enums.TradingSignalOrdersAttrs.ORDER_ID.value: buy_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: sell_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.CHAINED_TO.value: sell_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: ["1"],
        enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: {},
    }

    order_group = personal_data.OneCancelsTheOtherOrderGroup(
        "group_name",
        buy_limit_order.exchange_manager.exchange_personal_data.orders_manager
    )
    buy_limit_order.add_to_order_group(order_group)
    buy_limit_order.associate_to_entry("2")
    buy_limit_order.associate_to_entry("3")
    buy_limit_order.update_with_triggering_order_fees = False
    buy_limit_order.trigger_above = True
    buy_limit_order.trailing_profile = personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    final_order_desc = {
        enums.TradingSignalCommonsAttrs.ACTION.value: enums.TradingSignalOrdersActions.CREATE.value,
        enums.TradingSignalOrdersAttrs.SIDE.value: enums.TradeOrderSide.BUY.value,
        enums.TradingSignalOrdersAttrs.STRATEGY.value: "strat",
        enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/ETH",
        enums.TradingSignalOrdersAttrs.EXCHANGE.value: "binanceus",
        enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: enums.ExchangeTypes.SPOT.value,
        enums.TradingSignalOrdersAttrs.TYPE.value: enums.TraderOrderType.BUY_LIMIT.value,
        enums.TradingSignalOrdersAttrs.QUANTITY.value: float(buy_limit_order.origin_quantity),
        enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "10",
        enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: "8%",
        enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: True,
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: "10",
        enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: "8%",
        enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 111.545445445,
        enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 111.545445445,
        enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 111.1,
        enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 111.1,
        enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 111.0,
        enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 111.0,
        enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
        enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
        enums.TradingSignalOrdersAttrs.GROUP_ID.value: order_group.name,
        enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: personal_data.OneCancelsTheOtherOrderGroup.__name__,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: personal_data.StopFirstActiveOrderSwapStrategy.__name__,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: constants.ACTIVE_ORDER_STRATEGY_SWAP_TIMEOUT,
        enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value:
            personal_data.FilledTakeProfitTrailingProfile.get_type().value,
        enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: buy_limit_order.trailing_profile.to_dict(),
        enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: False,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value: 1.14,
        enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: True,
        enums.TradingSignalOrdersAttrs.TAG.value: "hello",
        enums.TradingSignalOrdersAttrs.ORDER_ID.value: buy_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: sell_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.CHAINED_TO.value: sell_limit_order.order_id,
        enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
        enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: ["1", "2", "3"],
        enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
        enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: {},
    }
    assert signals.create_order_signal_content(
        buy_limit_order,
        enums.TradingSignalOrdersActions.CREATE,
        "strat",
        exchange_manager,
        target_amount="1%",
        target_position="2",
        updated_target_amount="10",
        updated_target_position="8%",
        updated_limit_price=decimal.Decimal("111.545445445"),
        updated_stop_price=decimal.Decimal("111.1"),
        updated_current_price=decimal.Decimal("111"),
    ) == final_order_desc

    # with cleared order, gives the same signal
    buy_limit_order.clear()
    assert signals.create_order_signal_content(
        buy_limit_order,
        enums.TradingSignalOrdersActions.CREATE,
        "strat",
        exchange_manager,
        target_amount="1%",
        target_position="2",
        updated_target_amount="10",
        updated_target_position="8%",
        updated_limit_price=decimal.Decimal("111.545445445"),
        updated_stop_price=decimal.Decimal("111.1"),
        updated_current_price=decimal.Decimal("111"),
    ) == final_order_desc


def test_get_order_dependency(buy_limit_order):
    assert signals.get_order_dependency(buy_limit_order) == commons_signals.SignalDependencies([
        {enums.TradingSignalDependencies.ORDER_ID.value: buy_limit_order.order_id}
    ])


def get_orders_dependencies(buy_limit_order, sell_limit_order):
    assert signals.get_orders_dependencies([buy_limit_order, sell_limit_order]) == commons_signals.SignalDependencies([
        {enums.TradingSignalDependencies.ORDER_ID.value: buy_limit_order.order_id},
        {enums.TradingSignalDependencies.ORDER_ID.value: sell_limit_order.order_id}
    ])


def test_get_position_dependency():
    position = mock.Mock(symbol="BTC/USDT:USDT")
    assert signals.get_position_dependency(position) == commons_signals.SignalDependencies([
        {enums.TradingSignalDependencies.POSITION_SYMBOL.value: "BTC/USDT:USDT"}
    ])


def test_are_dependencies_filled():
    no_dep_signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={}
    )
    assert signals_util.are_dependencies_filled(no_dep_signal, []) is True
    single_dep_signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={},
        dependencies=signals.get_order_dependency(mock.Mock(order_id="123"))
    )
    assert signals_util.are_dependencies_filled(single_dep_signal, []) is False
    dual_dep_signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={},
        dependencies=signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="456")])
    )
    assert signals_util.are_dependencies_filled(dual_dep_signal, []) is False
    succeeded_signals = [
        commons_signals.Signal(
            topic=enums.TradingSignalTopics.ORDERS.value,
            content={
                enums.TradingSignalOrdersAttrs.ORDER_ID.value: "123"
            }
        )
    ]
    assert signals_util.are_dependencies_filled(no_dep_signal, succeeded_signals) is True
    # dep is filled
    assert signals_util.are_dependencies_filled(single_dep_signal, succeeded_signals) is True
    succeeded_signals.append(
        commons_signals.Signal(
            topic=enums.TradingSignalTopics.ORDERS.value,
            content={
                enums.TradingSignalOrdersAttrs.ORDER_ID.value: "456-wrong"  # not the expected id
            }
        )
    )
    assert signals_util.are_dependencies_filled(no_dep_signal, succeeded_signals) is True
    assert signals_util.are_dependencies_filled(single_dep_signal, succeeded_signals) is True
    assert signals_util.are_dependencies_filled(dual_dep_signal, succeeded_signals) is False
    succeeded_signals.append(
        commons_signals.Signal(
            topic=enums.TradingSignalTopics.ORDERS.value,
            content={
                enums.TradingSignalOrdersAttrs.ORDER_ID.value: "456"  # the last expected id
            }
        )
    )
    assert signals_util.are_dependencies_filled(no_dep_signal, succeeded_signals) is True
    assert signals_util.are_dependencies_filled(single_dep_signal, succeeded_signals) is True
    assert signals_util.are_dependencies_filled(dual_dep_signal, succeeded_signals) is True


def test_get_signals_filled_dependencies():
    assert signals_util._get_signals_filled_dependencies([]) == commons_signals.SignalDependencies()
    signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={}
    )
    assert signals_util._get_signals_filled_dependencies([signal]) == commons_signals.SignalDependencies()
    signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={
            enums.TradingSignalOrdersAttrs.ORDER_ID.value: "123"
        }
    )
    assert signals_util._get_signals_filled_dependencies([signal]) == commons_signals.SignalDependencies([
        {enums.TradingSignalDependencies.ORDER_ID.value: "123"}
    ])
    signal_2 = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={
            enums.TradingSignalOrdersAttrs.ORDER_ID.value: "456"
        }
    )
    signal_3 = commons_signals.Signal(
        topic=enums.TradingSignalTopics.POSITIONS.value,
        content={
            enums.TradingSignalPositionsAttrs.SYMBOL.value: "BTC/USDT:USDT"
        }
    )
    assert signals_util._get_signals_filled_dependencies([signal, signal_2, signal_3]) == commons_signals.SignalDependencies([
        {enums.TradingSignalDependencies.ORDER_ID.value: "123"},
        {enums.TradingSignalDependencies.ORDER_ID.value: "456"},
        {enums.TradingSignalDependencies.POSITION_SYMBOL.value: "BTC/USDT:USDT"}
    ])

def test_get_signal_filled_dependency():
    signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={}
    )
    assert signals_util._get_signal_filled_dependency(signal) == None
    signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.ORDERS.value,
        content={
            enums.TradingSignalOrdersAttrs.ORDER_ID.value: "123"
        }
    )
    assert signals_util._get_signal_filled_dependency(signal) == {
        enums.TradingSignalDependencies.ORDER_ID.value: "123"
    }
    
    signal = commons_signals.Signal(
        topic=enums.TradingSignalTopics.POSITIONS.value,
        content={
            enums.TradingSignalPositionsAttrs.SYMBOL.value: "BTC/USDT:USDT"
        }
    )
    assert signals_util._get_signal_filled_dependency(signal) == {
        enums.TradingSignalDependencies.POSITION_SYMBOL.value: "BTC/USDT:USDT"
    }

    with pytest.raises(NotImplementedError):
        signals_util._get_signal_filled_dependency(commons_signals.Signal(
            topic="unknown_topic",
            content={}
        ))
