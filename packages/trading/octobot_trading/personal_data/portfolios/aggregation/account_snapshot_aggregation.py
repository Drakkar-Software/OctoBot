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

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.orders.order_util as order_util_module


def sum_numeric_holdings(
    left_value: typing.Union[float, decimal.Decimal, int],
    right_value: typing.Union[float, decimal.Decimal, int],
) -> typing.Union[float, decimal.Decimal]:
    if isinstance(left_value, decimal.Decimal) or isinstance(right_value, decimal.Decimal):
        return decimal.Decimal(str(left_value)) + decimal.Decimal(str(right_value))
    return left_value + right_value


def merge_portfolio_contents(
    target: dict[str, dict],
    source: dict[str, dict],
) -> None:
    for asset_name, holdings in source.items():
        if asset_name not in target:
            target[asset_name] = dict(holdings)
            continue
        merged_holdings = target[asset_name]
        for holding_key, holding_value in holdings.items():
            if holding_key in merged_holdings:
                merged_holdings[holding_key] = sum_numeric_holdings(
                    merged_holdings[holding_key],
                    holding_value,
                )
            else:
                merged_holdings[holding_key] = holding_value


def merge_enriched_orders_deduped(
    existing_orders: list[dict],
    new_orders: list[dict],
) -> list[dict]:
    exchange_id_column = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
    orders_with_exchange_id = [
        order
        for order in existing_orders
        if order.get(trading_constants.STORAGE_ORIGIN_VALUE, {}).get(exchange_id_column) is not None
    ]
    orders_without_exchange_id = [
        order
        for order in existing_orders
        if order.get(trading_constants.STORAGE_ORIGIN_VALUE, {}).get(exchange_id_column) is None
    ]
    orders_by_exchange_id = order_util_module.get_enriched_orders_by_exchange_id(
        orders_with_exchange_id
    )
    for order in new_orders:
        exchange_order_id = order.get(trading_constants.STORAGE_ORIGIN_VALUE, {}).get(
            exchange_id_column
        )
        if exchange_order_id is None:
            orders_without_exchange_id.append(order)
            continue
        orders_by_exchange_id[exchange_order_id] = order
    return list(orders_by_exchange_id.values()) + orders_without_exchange_id
