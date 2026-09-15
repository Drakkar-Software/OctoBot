#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums


def is_simulated_order_filled(order_price: float, market_price: float, trigger_above: bool) -> bool:
    if trigger_above:
        return market_price >= order_price
    return market_price <= order_price


def resolve_trigger_above(inner_order: dict) -> bool:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    if order_columns.TRIGGER_ABOVE.value in inner_order:
        return bool(inner_order[order_columns.TRIGGER_ABOVE.value])
    order_side = inner_order.get(order_columns.SIDE.value)
    if order_side == trading_enums.TradeOrderSide.SELL.value:
        return True
    return False


def resolve_simulated_open_orders(
    open_orders: list[dict],
    ticker_close_by_symbol: dict[str, float],
) -> list[dict]:
    still_open_orders: list[dict] = []
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    for open_order in open_orders:
        inner_order = open_order.get(trading_constants.STORAGE_ORIGIN_VALUE, open_order)
        symbol = inner_order.get(order_columns.SYMBOL.value)
        order_price = inner_order.get(order_columns.PRICE.value)
        if symbol is None or order_price is None:
            still_open_orders.append(open_order)
            continue
        if symbol not in ticker_close_by_symbol:
            commons_logging.get_logger(__name__).warning(
                "No ticker close for %s, keeping simulated order open",
                symbol,
            )
            still_open_orders.append(open_order)
            continue
        trigger_above = resolve_trigger_above(inner_order)
        market_price = ticker_close_by_symbol[symbol]
        if is_simulated_order_filled(float(order_price), market_price, trigger_above):
            continue
        still_open_orders.append(open_order)
    return still_open_orders


def symbols_from_open_orders(open_orders: list[dict]) -> list[str]:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    symbols: set[str] = set()
    for open_order in open_orders:
        inner_order = open_order.get(trading_constants.STORAGE_ORIGIN_VALUE, open_order)
        symbol = inner_order.get(order_columns.SYMBOL.value)
        if symbol is not None:
            symbols.add(str(symbol))
    return sorted(symbols)
