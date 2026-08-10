#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums


def detect_changed_order_ids(
    previous_open_order_exchange_ids: set[str],
    current_open_orders: list,
) -> set[str]:
    if not previous_open_order_exchange_ids:
        return set()
    current_open_order_exchange_ids = open_order_exchange_ids_from_open_orders(current_open_orders)
    return previous_open_order_exchange_ids - current_open_order_exchange_ids


def open_order_exchange_ids_from_protocol_orders(
    protocol_orders: list[protocol_models.Order] | None,
) -> set[str]:
    if not protocol_orders:
        return set()
    return {
        str(protocol_order.exchange_id)
        for protocol_order in protocol_orders
        if protocol_order.exchange_id
    }


def open_order_exchange_ids_from_open_orders(open_orders: list) -> set[str]:
    exchange_ids: set[str] = set()
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    for open_order in open_orders:
        order_dict = open_order_to_storage_dict(open_order)
        inner_order = order_dict.get(trading_constants.STORAGE_ORIGIN_VALUE, order_dict)
        if not isinstance(inner_order, dict):
            inner_order = order_dict
        exchange_id = inner_order.get(order_columns.EXCHANGE_ID.value) or inner_order.get(
            order_columns.ID.value
        )
        if exchange_id is not None:
            exchange_ids.add(str(exchange_id))
    return exchange_ids


def open_order_to_storage_dict(open_order) -> dict:
    if isinstance(open_order, dict):
        return open_order
    if hasattr(open_order, "to_dict"):
        return open_order.to_dict()
    if hasattr(open_order, "order"):
        return open_order.order
    raise TypeError(f"Unsupported open order type: {type(open_order).__name__}")
