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
import typing

import octobot_commons.signals as signals
import octobot_trading.signals.util as signal_util
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.constants as trading_constants


class TradingSignalBundleBuilder(signals.SignalBundleBuilder):
    def __init__(self, identifier: str, strategy: str):
        super().__init__(identifier)
        self.strategy = strategy

    def build(self) -> signals.SignalBundle:
        """
        Link bundled an grouped orders and create a signal_bundle.SignalBundle from registered signals
        """
        self._pack_referenced_orders_together()
        return super().build()

    def sort_signals(self):
        # https://docs.python.org/3/howto/sorting.html#sort-stability-and-complex-sorts
        # sorting rules:
        #   1. cancelled order signals at the beginning of the list
        #   2. positions edit (such as changing leverage)
        #   3. others as is while keeping initial order
        def _sort_key(signal: signals.Signal):
            return (
                0 if (
                    signal.content[trading_enums.TradingSignalCommonsAttrs.ACTION.value] ==
                    trading_enums.TradingSignalOrdersActions.CANCEL.value
                ) else (
                    1 if signal.topic == trading_enums.TradingSignalTopics.POSITIONS.value
                    else 2
                )
            )

        self.signals = sorted(self.signals, key=_sort_key)
        return self

    def add_created_order(
        self, order, exchange_manager, target_amount=None, 
        target_position=None, dependencies: typing.Optional[signals.SignalDependencies] = None
    ):
        if target_amount is None and target_position is None:
            raise trading_errors.InvalidArgumentError("target_amount or target_position has to be provided")
        if not self._update_pending_orders(order, exchange_manager,
                                           trading_enums.TradingSignalOrdersActions.CREATE,
                                           target_amount=target_amount,
                                           target_position=target_position,
                                           dependencies=dependencies):
            self.register_signal(
                trading_enums.TradingSignalTopics.ORDERS.value,
                signal_util.create_order_signal_content(
                    order,
                    trading_enums.TradingSignalOrdersActions.CREATE,
                    self.strategy,
                    exchange_manager,
                    target_amount=target_amount,
                    target_position=target_position,
                ),
                dependencies=dependencies
            )

    def add_order_to_group(
        self, order, exchange_manager, dependencies: typing.Optional[signals.SignalDependencies] = None
    ):
        if not self._update_pending_orders(order, exchange_manager,
                                           trading_enums.TradingSignalOrdersActions.ADD_TO_GROUP,
                                           dependencies=dependencies):
            self.register_signal(
                trading_enums.TradingSignalTopics.ORDERS.value,
                signal_util.create_order_signal_content(
                    order,
                    trading_enums.TradingSignalOrdersActions.ADD_TO_GROUP,
                    self.strategy,
                    exchange_manager
                ),
                dependencies=dependencies
            )

    def add_edited_order(
            self, order, exchange_manager,
            updated_target_amount=None,
            updated_target_position=None,
            updated_limit_price=trading_constants.ZERO,
            updated_stop_price=trading_constants.ZERO,
            updated_current_price=trading_constants.ZERO,
            dependencies: typing.Optional[signals.SignalDependencies] = None,
    ):
        if updated_target_amount is updated_target_position is None and \
           updated_limit_price is updated_stop_price is updated_current_price is trading_constants.ZERO:
            raise trading_errors.InvalidArgumentError("an updated argument has to be provided")
        if not self._update_pending_orders(
                order,
                exchange_manager,
                trading_enums.TradingSignalOrdersActions.EDIT,
                updated_target_amount=updated_target_amount,
                updated_target_position=updated_target_position,
                updated_limit_price=updated_limit_price,
                updated_stop_price=updated_stop_price,
                updated_current_price=updated_current_price,
                dependencies=dependencies
        ):
            self.register_signal(
                trading_enums.TradingSignalTopics.ORDERS.value,
                signal_util.create_order_signal_content(
                    order,
                    trading_enums.TradingSignalOrdersActions.EDIT,
                    self.strategy,
                    exchange_manager,
                    updated_target_amount=updated_target_amount,
                    updated_target_position=updated_target_position,
                    updated_limit_price=updated_limit_price,
                    updated_stop_price=updated_stop_price,
                    updated_current_price=updated_current_price,
                ),
                dependencies=dependencies
            )

    def add_cancelled_order(
        self, order, exchange_manager, dependencies: typing.Optional[signals.SignalDependencies] = None
    ):
        if not self._update_pending_orders(
            order, exchange_manager, trading_enums.TradingSignalOrdersActions.CANCEL, dependencies=dependencies
        ):
            self.register_signal(
                trading_enums.TradingSignalTopics.ORDERS.value,
                signal_util.create_order_signal_content(
                    order,
                    trading_enums.TradingSignalOrdersActions.CANCEL,
                    self.strategy,
                    exchange_manager,
                ),
                dependencies=dependencies
            )

    def add_leverage_update(
        self, symbol: str, side: typing.Optional[trading_enums.PositionSide],
        leverage: decimal.Decimal, exchange_manager, 
        dependencies: typing.Optional[signals.SignalDependencies] = None
    ):
        if not self._update_pending_positions(
            symbol, side, exchange_manager, trading_enums.TradingSignalPositionsActions.EDIT, leverage=leverage
        ):
            self.register_signal(
                trading_enums.TradingSignalTopics.POSITIONS.value,
                signal_util.create_position_signal_content(
                    trading_enums.TradingSignalPositionsActions.EDIT,
                    self.strategy,
                    exchange_manager,
                    symbol,
                    side,
                    leverage,
                ),
                dependencies=dependencies
            )

    def _update_pending_orders(
        self, order, exchange_manager,
        action,
        target_amount=None,
        target_position=None,
        updated_target_amount=None,
        updated_target_position=None,
        updated_limit_price=trading_constants.ZERO,
        updated_stop_price=trading_constants.ZERO,
        updated_current_price=trading_constants.ZERO,
        dependencies: typing.Optional[signals.SignalDependencies] = None,
    ):
        try:
            index, order_description = self._get_order_description_from_local_orders(order.order_id)
            if action is trading_enums.TradingSignalOrdersActions.CREATE:
                # replace order
                self.signals[index] = self.create_signal(
                    trading_enums.TradingSignalTopics.ORDERS.value,
                    signal_util.create_order_signal_content(
                        order,
                        trading_enums.TradingSignalOrdersActions.CREATE,
                        self.strategy,
                        exchange_manager,
                        target_amount=target_amount,
                        target_position=target_position
                    ),
                    dependencies=dependencies
                )
            if action is trading_enums.TradingSignalOrdersActions.ADD_TO_GROUP:
                # update order group
                order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value] = order.order_group.name
                order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value] = \
                    order.order_group.__class__.__name__
                order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value] = \
                    order.order_group.active_order_swap_strategy.__class__.__name__
                order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value] = \
                    order.order_group.active_order_swap_strategy.swap_timeout
                order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value] = \
                    order.order_group.active_order_swap_strategy.trigger_price_configuration
            elif action is trading_enums.TradingSignalOrdersActions.EDIT:
                # avoid editing order that are not yet created
                order_description[trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value] = \
                    updated_target_amount
                order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value] = \
                    updated_target_amount
                order_description[trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value] = \
                    updated_target_position
                order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value] = \
                    updated_target_position
                order_description[trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value] = \
                    float(updated_limit_price)
                order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value] = \
                    float(updated_limit_price)
                order_description[trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value] = \
                    float(updated_stop_price)
                order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value] = \
                    float(updated_stop_price)
                order_description[trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value] = \
                    float(updated_current_price)
                order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value] = \
                    float(updated_current_price)
            elif action is trading_enums.TradingSignalOrdersActions.CANCEL:
                if order_description[trading_enums.TradingSignalCommonsAttrs.ACTION.value] == \
                   trading_enums.TradingSignalOrdersActions.CREATE.value:
                    # avoid creating order that are to be cancelled
                    self.signals.pop(index)
                else:
                    # now cancel order (no need to perform previous actions as it will get cancelled anyway
                    order_description[trading_enums.TradingSignalCommonsAttrs.ACTION.value] = \
                        trading_enums.TradingSignalOrdersActions.CANCEL.value
            return True
        except trading_errors.OrderDescriptionNotFoundError:
            pass
        return False

    def _update_pending_positions(self, symbol, side, exchange_manager, action, leverage):
        try:
            _, position_description = self._get_position_description_from_local_positions(
                symbol, side, exchange_manager.exchange_name
            )
            if action is trading_enums.TradingSignalPositionsActions.EDIT:
                # update position edit content
                position_description[trading_enums.TradingSignalPositionsAttrs.LEVERAGE.value] = float(leverage)
            return True
        except trading_errors.PositionDescriptionNotFoundError:
            pass
        return False

    def _pack_referenced_orders_together(self):
        filtered_signals = []
        order_description_by_seen_group_ids = {}
        for signal in self.signals:
            include_signal = True
            if signal.topic == trading_enums.TradingSignalTopics.ORDERS.value:
                try:
                    # bundled orders must be sent at the same time as the original order, add them both to the same signal
                    if add_to_order_id := signal.content[trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value]:
                        _, order_description = self._get_order_description_from_local_orders(add_to_order_id)
                        order_description[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value]\
                            .append(signal.content)
                        include_signal = False
                    # chained orders must be sent at the same time as the original order, add them both to the same signal
                    elif add_to_order_id := signal.content[trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value]:
                        _, order_description = self._get_order_description_from_local_orders(add_to_order_id)
                        order_description[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value]\
                            .append(signal.content)
                        include_signal = False
                except trading_errors.OrderDescriptionNotFoundError:
                    # Failed to find the triggering order's associated signal that this order signal should be associated to
                    # in ADDITIONAL_ORDERS.
                    # This can happen when the triggering order has already been sent in a different signal
                    self.logger.debug(f"Skip signal packing for {signal}: triggering order not found in associated signals")
                # grouped orders must be created before the group is enabled, add them both to the same signal
                # groups. They might also need to be updated together
                if (add_to_group_ids := signal.content[trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value]) \
                   and include_signal:
                    if add_to_group_ids in order_description_by_seen_group_ids:
                        order_description_by_seen_group_ids[add_to_group_ids][
                            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(signal.content)
                        include_signal = False
                    else:
                        order_description_by_seen_group_ids[add_to_group_ids] = signal.content
            elif signal.topic == trading_enums.TradingSignalTopics.POSITIONS.value:
                # nothing to do, signals can be added as is
                pass
            else:
                include_signal = False
                self.logger.debug(f"Skip signal packing for {signal} ({signal.topic=})")
            if include_signal:
                filtered_signals.append(signal)
        self.signals = filtered_signals

    def _get_order_description_from_local_orders(self, order_id):
        for index, signal in enumerate(self.signals):
            if (
                signal.topic == trading_enums.TradingSignalTopics.ORDERS.value and
                signal.content[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value] == order_id
            ):
                return index, signal.content
        raise trading_errors.OrderDescriptionNotFoundError(
            f"order not found (order_id: {order_id})"
        )

    def _get_position_description_from_local_positions(self, symbol, side, exchange_name):
        for index, signal in enumerate(self.signals):
            side_value = side.value if side else side
            if (
                signal.topic == trading_enums.TradingSignalTopics.POSITIONS.value and
                signal.content[trading_enums.TradingSignalPositionsAttrs.SYMBOL.value] == symbol and
                signal.content[trading_enums.TradingSignalPositionsAttrs.SIDE.value] == side_value and
                signal.content[trading_enums.TradingSignalPositionsAttrs.EXCHANGE.value] == exchange_name
            ):
                return index, signal.content
        raise trading_errors.PositionDescriptionNotFoundError(
            f"position not found ({symbol, side, exchange_name})"
        )

