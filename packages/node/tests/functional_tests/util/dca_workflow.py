#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""DCA-specific helpers for simulator automation DBOS functional tests."""

from __future__ import annotations

import datetime
import decimal
import typing
import uuid

import octobot_trading.constants as trading_constants_module
import octobot_trading.enums as trading_enums_module
import octobot_protocol.models as protocol_models_module

from . import price_mocks as price_mocks_module
from . import workflow_common as workflow_common_module

BTC_USDC = "BTC/USDC"
ETH_USDC = "ETH/USDC"
TRADED_SYMBOLS = (BTC_USDC, ETH_USDC)
FIXED_BTC_USDC_CLOSE = 100000.0
FIXED_ETH_USDC_CLOSE = 2000.0
D_ENTRY_LIMIT_PERCENT = decimal.Decimal("0.015")
D_SECONDARY_ENTRY_STEP_PERCENT = decimal.Decimal("0.01")
PRICE_TOLERANCE = decimal.Decimal("0.5")

SIMULATOR_DCA_DEFAULT_STRATEGY_ID = "simulator-dca-functional-default-strategy"


def default_close_prices_by_symbol() -> dict[str, float]:
    return {
        BTC_USDC: FIXED_BTC_USDC_CLOSE,
        ETH_USDC: FIXED_ETH_USDC_CLOSE,
    }


def _close_to_decimal(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    if isinstance(close, decimal.Decimal):
        return close
    return decimal.Decimal(str(close))


def initial_buy_price(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    close_decimal = _close_to_decimal(close)
    return close_decimal * (decimal.Decimal("1") - D_ENTRY_LIMIT_PERCENT)


def secondary_buy_price(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    close_decimal = _close_to_decimal(close)
    return close_decimal * (
        decimal.Decimal("1") - D_ENTRY_LIMIT_PERCENT - D_SECONDARY_ENTRY_STEP_PERCENT
    )


def d_order_price(price: typing.Any) -> decimal.Decimal:
    return decimal.Decimal(str(price))


def open_order_origins_from_exchange_elements(
    exchange_account_elements: typing.Any,
) -> list[dict]:
    orders_container = getattr(exchange_account_elements, "orders", None)
    if orders_container is None and isinstance(exchange_account_elements, dict):
        orders_container = exchange_account_elements.get("orders")
    if orders_container is None:
        return []
    open_orders = getattr(orders_container, "open_orders", None)
    if open_orders is None and isinstance(orders_container, dict):
        open_orders = orders_container.get("open_orders", [])
    storage_key = trading_constants_module.STORAGE_ORIGIN_VALUE
    return [
        order_document[storage_key]
        for order_document in (open_orders or [])
        if isinstance(order_document, dict) and storage_key in order_document
    ]


def sorted_orders_by_side_and_symbol(
    open_orders: list[dict],
    side: str,
    symbol: str,
) -> list[dict]:
    price_column = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
    symbol_column = trading_enums_module.ExchangeConstantsOrderColumns.SYMBOL.value
    side_column = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
    matching_orders = [
        order
        for order in open_orders
        if order.get(side_column) == side and order.get(symbol_column) == symbol
    ]
    return sorted(matching_orders, key=lambda order: d_order_price(order[price_column]))


def lowest_buy_price_for_symbol(open_orders: list[dict], symbol: str) -> decimal.Decimal:
    buy_orders_for_symbol = sorted_orders_by_side_and_symbol(
        open_orders,
        trading_enums_module.TradeOrderSide.BUY.value,
        symbol,
    )
    price_column = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
    return d_order_price(buy_orders_for_symbol[0][price_column])


def globally_lowest_buy_order(open_orders: list[dict]) -> dict:
    price_column = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
    side_column = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
    buy_orders = [
        order
        for order in open_orders
        if order.get(side_column) == trading_enums_module.TradeOrderSide.BUY.value
    ]
    assert buy_orders, "expected at least one open buy order"
    return min(buy_orders, key=lambda order: d_order_price(order[price_column]))


def drop_close_below_order_price(
    close_by_symbol: dict[str, float],
    order: dict,
    *,
    margin: decimal.Decimal = decimal.Decimal("10"),
) -> str:
    symbol_column = trading_enums_module.ExchangeConstantsOrderColumns.SYMBOL.value
    price_column = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
    symbol = order[symbol_column]
    order_price = d_order_price(order[price_column])
    close_by_symbol[symbol] = float(order_price - margin)
    return symbol


def assert_open_buy_ladder_for_symbol(
    open_orders: list[dict],
    *,
    symbol: str,
    close: float,
) -> None:
    buy_orders_for_symbol = sorted_orders_by_side_and_symbol(
        open_orders,
        trading_enums_module.TradeOrderSide.BUY.value,
        symbol,
    )
    assert len(buy_orders_for_symbol) == 2
    price_column = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
    buy_prices = [d_order_price(order[price_column]) for order in buy_orders_for_symbol]
    expected_initial = initial_buy_price(close)
    expected_secondary = secondary_buy_price(close)
    highest_buy_price = max(buy_prices)
    lowest_buy_price = min(buy_prices)
    assert abs(highest_buy_price - expected_initial) <= PRICE_TOLERANCE
    assert abs(lowest_buy_price - expected_secondary) <= PRICE_TOLERANCE


def is_dca_entry_baseline(buy_count: int, sell_count: int, trade_count: int) -> bool:
    return buy_count == 4 and sell_count == 0 and trade_count == 0


def is_dca_after_symbol_fill_progress(
    buy_count: int,
    sell_count: int,
    trade_count: int,
) -> bool:
    return buy_count == 4 and trade_count >= 1


def is_dca_after_lowest_buy_fill_and_retrigger(
    buy_count: int,
    sell_count: int,
    trade_count: int,
) -> bool:
    return buy_count == 4 and sell_count >= 2 and trade_count >= 2


def symbol_has_open_sell_order(open_orders: list[dict], symbol: str) -> bool:
    sell_orders_for_symbol = sorted_orders_by_side_and_symbol(
        open_orders,
        trading_enums_module.TradeOrderSide.SELL.value,
        symbol,
    )
    return len(sell_orders_for_symbol) >= 1


def both_symbols_have_open_sell_orders(open_orders: list[dict]) -> bool:
    return all(symbol_has_open_sell_order(open_orders, symbol) for symbol in TRADED_SYMBOLS)


def tickers_repository_fetch_tickers_close_override(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    return price_mocks_module.tickers_repository_fetch_tickers_close_override(
        get_close_price_for_symbol,
        traded_symbols=TRADED_SYMBOLS,
    )


def dca_configuration_for_functional_no_evaluator() -> protocol_models_module.DCAConfiguration:
    return protocol_models_module.DCAConfiguration(
        configuration_type=protocol_models_module.ActionConfigurationType.DCA,
        symbols=list(TRADED_SYMBOLS),
        buy_orders_count=2,
        percent_amount_per_buy_order=8,
        profit_target_percent=1.75,
        buy_order_price_discount_percent=1.5,
        enable_stop_loss=False,
        stop_loss_price_discount_percent=0,
        trigger_mode="Always trigger long",
        use_init_entry_orders=True,
        time_frames=[],
        evaluators=[],
    )


def seeded_dca_strategy_for_functional_wallet(
    *,
    stored_strategy_id: str,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Simulator DCA automation strategy",
        reference_market="USDC",
        configuration=protocol_models_module.StrategyConfiguration(
            dca_configuration_for_functional_no_evaluator(),
        ),
    )


def build_create_dca_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str | None = None,
    emit_signals: bool | None = None,
) -> protocol_models_module.UserAction:
    reference_strategy_identifier = strategy_id or SIMULATOR_DCA_DEFAULT_STRATEGY_ID
    strategy_reference = protocol_models_module.StrategyReference(
        id=reference_strategy_identifier,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        emit_signals=emit_signals if emit_signals is not None else False,
    )
    automation_configuration = protocol_models_module.AutomationConfiguration(
        name=name,
        created_at=datetime.datetime(2026, 5, 10, 8, 0, 0, tzinfo=datetime.UTC),
        strategy=strategy_reference,
        accounts=[protocol_models_module.AccountReference(id=account_id)],
    )
    payload = protocol_models_module.CreateAutomationConfiguration(
        action_type=protocol_models_module.UserActionType.AUTOMATION_CREATE,
        configuration=automation_configuration,
    )
    return protocol_models_module.UserAction(
        id=f"ua-dca-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )
