# pylint: disable=W0706
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

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.constants as constants
import octobot_trading.enums as enums


def to_protocol_order(
    storage_or_base_order: dict[str, typing.Any]
) -> protocol_models.Order:
    order_details = storage_or_base_order.get(constants.STORAGE_ORIGIN_VALUE, storage_or_base_order)
    protocol_order = protocol_models.Order(
        id=order_details[enums.ExchangeConstantsOrderColumns.ID.value],
        symbol=order_details[enums.ExchangeConstantsOrderColumns.SYMBOL.value],
        price=float(order_details[enums.ExchangeConstantsOrderColumns.PRICE.value]),
        quantity=float(order_details[enums.ExchangeConstantsOrderColumns.AMOUNT.value]),
        filled=float(order_details[enums.ExchangeConstantsOrderColumns.FILLED.value]),
        exchange_id=order_details[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value],
        side=order_details[enums.ExchangeConstantsOrderColumns.SIDE.value],
        type=order_details[enums.ExchangeConstantsOrderColumns.TYPE.value],
        trigger_above=order_details[enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value],
        reduce_only=order_details[enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value],
        is_active=order_details[enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value],
        status=order_details[enums.ExchangeConstantsOrderColumns.STATUS.value],
        created_at=timestamp_util.utc_datetime_from_timestamp(order_details[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value]),
    )
    if entries := storage_or_base_order.get(enums.StoredOrdersAttr.ENTRIES.value):
        protocol_order.entries = entries
    if order_group := storage_or_base_order.get(enums.StoredOrdersAttr.GROUP.value):
        protocol_order.order_group = protocol_models.OrderGroup(
            id=order_group[enums.StoredOrdersAttr.GROUP_ID.value],
            type=order_group[enums.StoredOrdersAttr.GROUP_TYPE.value],
        )
        if active_order_swap_strategy := order_group.get(enums.StoredOrdersAttr.ORDER_SWAP_STRATEGY.value):
            protocol_order.order_group.active_order_swap_strategy = protocol_models.ActiveOrderSwapStrategy(
                type=active_order_swap_strategy[enums.StoredOrdersAttr.STRATEGY_TYPE.value],
                trigger_price_configuration=active_order_swap_strategy[enums.StoredOrdersAttr.STRATEGY_TRIGGER_CONFIG.value],
                timeout=active_order_swap_strategy[enums.StoredOrdersAttr.STRATEGY_TIMEOUT.value],
            )
    if trailing_profile := storage_or_base_order.get(enums.StoredOrdersAttr.TRAILING_PROFILE.value):
        protocol_order.trailing_profile = protocol_models.TrailingProfile(
            type=trailing_profile[enums.StoredOrdersAttr.TRAILING_PROFILE_TYPE.value],
            details=trailing_profile[enums.StoredOrdersAttr.TRAILING_PROFILE_DETAILS.value],
        )
    if cancel_policy := storage_or_base_order.get(enums.StoredOrdersAttr.CANCEL_POLICY.value):
        protocol_order.cancel_policy = protocol_models.CancelPolicy(
            type=cancel_policy[enums.StoredOrdersAttr.CANCEL_POLICY.value],
            details=cancel_policy[enums.StoredOrdersAttr.CANCEL_KWARGS.value],
        )
    if chained_orders := storage_or_base_order.get(enums.StoredOrdersAttr.CHAINED_ORDERS.value):
        protocol_order.chained_orders = [to_protocol_order(chained_order) for chained_order in chained_orders]
    return protocol_order


def exchange_columns_dict_from_protocol_order(
    order: protocol_models.Order,
) -> dict[str, typing.Any]:
    """
    Build a dict keyed by :class:`ExchangeConstantsOrderColumns` string values, suitable for
    :func:`parse_order_type` and other helpers that expect flattened exchange column payloads.
    """
    return {
        enums.ExchangeConstantsOrderColumns.SIDE.value: order.side.value,
        enums.ExchangeConstantsOrderColumns.TYPE.value: order.type.value,
        enums.ExchangeConstantsOrderColumns.SYMBOL.value: order.symbol,
        enums.ExchangeConstantsOrderColumns.PRICE.value: order.price,
        enums.ExchangeConstantsOrderColumns.AMOUNT.value: order.quantity,
        enums.ExchangeConstantsOrderColumns.FILLED.value: order.filled,
        enums.ExchangeConstantsOrderColumns.ID.value: order.id,
        enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: order.exchange_id,
        enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: order.trigger_above,
        enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: order.reduce_only,
        enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value: order.is_active,
        enums.ExchangeConstantsOrderColumns.STATUS.value: order.status.value,
        enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: order.created_at.timestamp(),
    }
