#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Typed accessors for flow exchange account elements in functional tests."""

from __future__ import annotations

import decimal
import enum
import typing

import octobot_commons.constants as commons_constants
import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_module
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

ExchangeAccountElementsInput = (
    exchange_account_elements_module.ExchangeAccountElements
    | dict[str, typing.Any]
    | None
)


def resolve_exchange_account_elements(
    elements: ExchangeAccountElementsInput,
) -> exchange_account_elements_module.ExchangeAccountElements | None:
    if elements is None:
        return None
    if isinstance(elements, dict):
        return exchange_account_elements_module.ExchangeAccountElements.from_dict(elements)
    return elements


def open_orders_from_elements(elements: ExchangeAccountElementsInput) -> list[dict]:
    resolved = resolve_exchange_account_elements(elements)
    if resolved is None:
        return []
    return list(resolved.orders.open_orders or [])


def trades_from_elements(elements: ExchangeAccountElementsInput) -> list[dict]:
    resolved = resolve_exchange_account_elements(elements)
    if resolved is None:
        return []
    return list(resolved.trades or [])


def portfolio_content_from_elements(elements: ExchangeAccountElementsInput) -> dict[str, typing.Any]:
    resolved = resolve_exchange_account_elements(elements)
    if resolved is None:
        return {}
    content = resolved.portfolio.content
    return content if isinstance(content, dict) else {}


def order_storage_payload(order_row: dict) -> dict:
    if not isinstance(order_row, dict):
        raise TypeError(f"expected order row dict, got {type(order_row).__name__}")
    storage_origin = trading_constants.STORAGE_ORIGIN_VALUE
    nested = order_row.get(storage_origin)
    if isinstance(nested, dict):
        return nested
    return order_row


def order_column_value(payload: dict, column: str) -> typing.Any:
    return payload.get(column)


def _decimal_order_price(raw: typing.Union[int, float, str, decimal.Decimal]) -> decimal.Decimal:
    if isinstance(raw, decimal.Decimal):
        return raw
    return decimal.Decimal(str(raw))


def _enum_column_value(raw: typing.Any) -> typing.Any:
    if isinstance(raw, enum.Enum):
        return raw.value
    return raw


normalize_order_column_value = _enum_column_value


def sorted_open_limit_prices_from_elements(
    elements: ExchangeAccountElementsInput,
    *,
    trade_order_side: trading_enums.TradeOrderSide,
) -> list[decimal.Decimal]:
    side_key = trading_enums.ExchangeConstantsOrderColumns.SIDE.value
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    type_col = trading_enums.ExchangeConstantsOrderColumns.TYPE.value
    want_side = trade_order_side.value
    limit_type = trading_enums.TradeOrderType.LIMIT.value
    prices: list[decimal.Decimal] = []
    for order_row in open_orders_from_elements(elements):
        if not isinstance(order_row, dict):
            raise TypeError(f"expected open order dict, got {type(order_row).__name__}")
        payload = order_storage_payload(order_row)
        side = _enum_column_value(order_column_value(payload, side_key))
        if side != want_side:
            continue
        price_raw = order_column_value(payload, price_col)
        if price_raw is None:
            continue
        order_type = _enum_column_value(order_column_value(payload, type_col))
        if order_type is not None and order_type != limit_type:
            continue
        prices.append(_decimal_order_price(price_raw))
    prices.sort()
    return prices


def sorted_open_limit_prices_from_protocol_orders(
    orders: typing.Iterable[protocol_models.Order] | None,
    *,
    trade_order_side: trading_enums.TradeOrderSide,
) -> list[decimal.Decimal]:
    if trade_order_side == trading_enums.TradeOrderSide.BUY:
        want_side = protocol_models.Side.BUY
    else:
        want_side = protocol_models.Side.SELL
    prices: list[decimal.Decimal] = []
    for order in orders or []:
        if not isinstance(order, protocol_models.Order):
            raise TypeError(f"expected protocol Order, got {type(order).__name__}")
        if order.side != want_side:
            continue
        if order.type != protocol_models.OrderType.LIMIT:
            continue
        if order.price is None:
            continue
        prices.append(_decimal_order_price(order.price))
    prices.sort()
    return prices


def portfolio_row_scalar(row: typing.Any, field_name: str) -> float:
    if not isinstance(row, dict):
        raise AssertionError(f"portfolio row must be a dict, got {type(row).__name__}: {row!r}")
    if field_name == commons_constants.PORTFOLIO_AVAILABLE:
        raw_value = row.get(commons_constants.PORTFOLIO_AVAILABLE)
        if raw_value is None:
            return portfolio_row_scalar(row, commons_constants.PORTFOLIO_TOTAL)
    elif field_name == commons_constants.PORTFOLIO_TOTAL:
        raw_value = row.get(commons_constants.PORTFOLIO_TOTAL)
    else:
        raw_value = row.get(field_name)
    if raw_value is None:
        raise AssertionError(f"portfolio row missing field {field_name!r}: {row!r}")
    return float(raw_value)


def portfolio_row_total(row: typing.Any) -> decimal.Decimal:
    if not isinstance(row, dict):
        raise AssertionError(f"portfolio row must be a dict, got {type(row).__name__}: {row!r}")
    raw_value = row.get(commons_constants.PORTFOLIO_TOTAL)
    if raw_value is None:
        raise AssertionError("portfolio row has no total amount")
    if isinstance(raw_value, decimal.Decimal):
        return raw_value
    return decimal.Decimal(str(raw_value))
