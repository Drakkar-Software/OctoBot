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
import typing
import dataclasses

import octobot_commons.signals as signals
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.constants as trading_constants


def create_order_signal_content(
    order, action, strategy, exchange_manager,
    target_amount=None,
    target_position=None,
    updated_target_amount=None,
    updated_target_position=None,
    updated_limit_price=trading_constants.ZERO,
    updated_stop_price=trading_constants.ZERO,
    updated_current_price=trading_constants.ZERO,
) -> dict:
    # only use order.order_id to identify orders in signals (exchange_order_id is local and never shared)
    return {
        trading_enums.TradingSignalCommonsAttrs.ACTION.value: action.value,
        trading_enums.TradingSignalOrdersAttrs.STRATEGY.value: strategy,
        trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: order.symbol,
        trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: exchange_manager.exchange_name,
        trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: exchanges.get_exchange_type(exchange_manager).value,
        trading_enums.TradingSignalOrdersAttrs.SIDE.value: order.side.value,
        trading_enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: order.trigger_above,
        trading_enums.TradingSignalOrdersAttrs.TYPE.value: order.order_type.value,
        trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: float(order.origin_quantity),
        trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: target_amount
        if updated_target_amount is None else updated_target_amount,
        trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: target_position
        if updated_target_position is None else updated_target_position,
        trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: updated_target_amount,
        trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: updated_target_position,
        trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: float(updated_limit_price)
        if updated_limit_price else float(order.origin_price),
        trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: float(updated_limit_price),
        trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: float(updated_stop_price)
        if updated_stop_price else float(order.origin_stop_price),
        trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: float(updated_stop_price),
        trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: float(updated_current_price)
        if updated_current_price else float(order.created_last_price),
        trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: float(updated_current_price),
        trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: order.reduce_only,
        trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
        trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value:
            None if order.order_group is None else order.order_group.name,
        trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
            None if order.order_group is None else order.order_group.__class__.__name__,
        trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: \
            order.order_group.active_order_swap_strategy.__class__.__name__ if order.order_group else None,
        trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: \
            order.order_group.active_order_swap_strategy.swap_timeout if order.order_group else None,
        trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: \
            order.order_group.active_order_swap_strategy.trigger_price_configuration if order.order_group else None,
        trading_enums.TradingSignalOrdersAttrs.TAG.value: order.tag,
        trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: order.associated_entry_ids,
        trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value:
            order.update_with_triggering_order_fees,
        trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: order.order_id,
        trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value:
            order.trailing_profile.get_type().value if order.trailing_profile else None,
        trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value:
            order.trailing_profile.to_dict() if order.trailing_profile else None,
        trading_enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: order.is_active,
        trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value:
            None if order.active_trigger is None else float(order.active_trigger.trigger_price),
        trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: None
            if order.active_trigger is None else order.active_trigger.trigger_above,
        trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value:
            order.cancel_policy.__class__.__name__ if order.cancel_policy else None,
        trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value:
            dataclasses.asdict(order.cancel_policy) if order.cancel_policy else None,
        trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value:
            None if order.triggered_by is None else order.triggered_by.order_id
        if order.has_been_bundled else None,
        trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value:
            None if order.triggered_by is None else order.triggered_by.order_id,
        trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
    }


def create_position_signal_content(
    action, strategy, exchange_manager, symbol, side, leverage
) -> dict:
    # only use order.order_id to identify orders in signals (exchange_order_id is local and never shared)
    return {
        trading_enums.TradingSignalCommonsAttrs.ACTION.value: action.value,
        trading_enums.TradingSignalPositionsAttrs.STRATEGY.value: strategy,
        trading_enums.TradingSignalPositionsAttrs.EXCHANGE.value: exchange_manager.exchange_name,
        trading_enums.TradingSignalPositionsAttrs.EXCHANGE_TYPE.value: exchanges.get_exchange_type(exchange_manager).value,
        trading_enums.TradingSignalPositionsAttrs.SYMBOL.value: symbol,
        trading_enums.TradingSignalPositionsAttrs.SIDE.value: side.value if side else side,
        trading_enums.TradingSignalPositionsAttrs.LEVERAGE.value: float(leverage),
    }


def get_orders_dependencies(orders: list) -> signals.SignalDependencies:
    return signals.SignalDependencies(
        [
            {
                trading_enums.TradingSignalDependencies.ORDER_ID.value: order.order_id
            }
            for order in orders
        ]
    )


def get_order_dependency(order) -> signals.SignalDependencies:
    return get_orders_dependencies([order])


def get_position_dependency(position) -> signals.SignalDependencies:
    return signals.SignalDependencies(
        [
            {
                trading_enums.TradingSignalDependencies.POSITION_SYMBOL.value: position.symbol
            }
        ]
    )


def are_dependencies_filled(signal: signals.Signal, succeeded_signals: list[signals.Signal]) -> bool:
    if not signal.dependencies:
        return True
    return signal.dependencies.is_filled_by(
        _get_signals_filled_dependencies(succeeded_signals)
    )


def _get_signals_filled_dependencies(succeeded_signals: list[signals.Signal]) -> signals.SignalDependencies:
    return signals.SignalDependencies(
        [
            filled_dependency
            for succeeded_signal in succeeded_signals
            if (filled_dependency := _get_signal_filled_dependency(succeeded_signal))
        ]
    )


def _get_signal_filled_dependency(signal: signals.Signal) -> typing.Optional[dict]:
    if signal.topic == trading_enums.TradingSignalTopics.ORDERS.value:
        if order_id := signal.content.get(
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value, None
        ):
            return {
                trading_enums.TradingSignalDependencies.ORDER_ID.value: order_id
            }
        return None
    if signal.topic == trading_enums.TradingSignalTopics.POSITIONS.value:
        if symbol := signal.content.get(
            trading_enums.TradingSignalPositionsAttrs.SYMBOL.value, None
        ):
            return {
                trading_enums.TradingSignalDependencies.POSITION_SYMBOL.value: symbol
            }
        return None
    raise NotImplementedError(f"Unsupported signal topic: {signal.topic}")
