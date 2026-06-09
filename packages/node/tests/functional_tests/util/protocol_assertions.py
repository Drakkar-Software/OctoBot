#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Protocol AutomationState assertion helpers for workflow functional tests."""

from __future__ import annotations

import math
import typing

import octobot_protocol.models as protocol_models_module

from . import workflow_common as workflow_common_module

buy_sell_trade_counts_from_exchange_elements = (
    workflow_common_module.buy_sell_trade_counts_from_exchange_elements
)


def portfolio_content_from_exchange_elements(exchange_account_elements: typing.Any) -> dict[str, typing.Any]:
    portfolio = getattr(exchange_account_elements, "portfolio", None)
    if portfolio is None and isinstance(exchange_account_elements, dict):
        portfolio = exchange_account_elements.get("portfolio")
    if portfolio is None:
        return {}
    content = getattr(portfolio, "content", None)
    if content is None and isinstance(portfolio, dict):
        content = portfolio.get("content")
    return content if isinstance(content, dict) else {}


def portfolio_row_scalar(row: typing.Any, field_name: str) -> float:
    if isinstance(row, dict):
        raw_value = row.get(field_name)
    else:
        raw_value = getattr(row, field_name, None)
    if raw_value is None and field_name == "available":
        return portfolio_row_scalar(row, "total")
    if raw_value is None:
        raise AssertionError(f"portfolio row missing field {field_name!r}: {row!r}")
    return float(raw_value)


def assert_protocol_automation_metadata_name(
    protocol_automation: protocol_models_module.AutomationState,
    expected_name: str,
) -> None:
    assert protocol_automation.metadata is not None, "expected AutomationState.metadata to be set"
    assert protocol_automation.metadata.name == expected_name, (
        f"AutomationState.metadata.name is {protocol_automation.metadata.name!r}; "
        f"expected {expected_name!r}"
    )


def assert_protocol_automation_matches_exchange_account_elements(
    protocol_automation: protocol_models_module.AutomationState,
    exchange_account_elements: typing.Any,
    *,
    expected_automation_task_status: protocol_models_module.WorkflowStatus,
    expected_order_symbol: str = "BTC/USDC",
    expected_exchange_account_id: str | None = None,
) -> None:
    if expected_exchange_account_id is not None:
        assert protocol_automation.exchange_account_ids == [expected_exchange_account_id], (
            f"AutomationState.exchange_account_ids is {protocol_automation.exchange_account_ids!r}; "
            f"expected {[expected_exchange_account_id]!r}"
        )
    assert protocol_automation.status == expected_automation_task_status, (
        f"AutomationState.status is {protocol_automation.status.value!r}; "
        f"expected {expected_automation_task_status.value!r}"
    )
    buy_orders, sell_orders, flow_trade_count = buy_sell_trade_counts_from_exchange_elements(
        exchange_account_elements,
    )
    expected_open_count = buy_orders + sell_orders
    protocol_orders = protocol_automation.orders or []
    protocol_trades = protocol_automation.trades or []
    assert len(protocol_orders) == expected_open_count, (
        f"protocol open order count {len(protocol_orders)} != flow open orders {expected_open_count} "
        f"(buy={buy_orders}, sell={sell_orders})"
    )
    assert len(protocol_trades) == flow_trade_count, (
        f"protocol trade count {len(protocol_trades)} != flow trade count {flow_trade_count}"
    )
    for order_summary in protocol_orders:
        assert order_summary.symbol == expected_order_symbol, (
            f"unexpected OrderSummary.symbol {order_summary.symbol!r}; expected {expected_order_symbol!r}"
        )
    content = portfolio_content_from_exchange_elements(exchange_account_elements)
    protocol_assets = protocol_automation.assets
    assert protocol_assets is not None, (
        "expected AutomationState.assets to be set"
    )
    assets_by_symbol = {asset.symbol: asset for asset in protocol_assets}
    for symbol, row in content.items():
        matching_asset = assets_by_symbol.get(symbol)
        assert matching_asset is not None, (
            f"missing protocol Asset for portfolio symbol {symbol!r}; "
            f"protocol asset symbols: {sorted(assets_by_symbol)!r}"
        )
        expected_total = portfolio_row_scalar(row, "total")
        expected_available = portfolio_row_scalar(row, "available")
        if not math.isclose(float(matching_asset.total), expected_total, rel_tol=1e-9, abs_tol=1e-6):
            raise AssertionError(
                f"Asset.total mismatch for {symbol!r}: protocol={matching_asset.total!r} "
                f"flow={expected_total!r}"
            )
        if not math.isclose(float(matching_asset.available), expected_available, rel_tol=1e-9, abs_tol=1e-6):
            raise AssertionError(
                f"Asset.available mismatch for {symbol!r}: protocol={matching_asset.available!r} "
                f"flow={expected_available!r}"
            )


def assert_protocol_automation_matches_exchange_account_elements_multi_symbol(
    protocol_automation: protocol_models_module.AutomationState,
    exchange_account_elements: typing.Any,
    *,
    expected_automation_task_status: protocol_models_module.WorkflowStatus | None = None,
    acceptable_automation_task_statuses: tuple[protocol_models_module.WorkflowStatus, ...] | None = None,
    expected_exchange_account_id: str | None = None,
    allowed_order_symbols: tuple[str, ...],
) -> None:
    if expected_exchange_account_id is not None:
        assert protocol_automation.exchange_account_ids == [expected_exchange_account_id], (
            f"AutomationState.exchange_account_ids is {protocol_automation.exchange_account_ids!r}; "
            f"expected {[expected_exchange_account_id]!r}"
        )
    if acceptable_automation_task_statuses is not None:
        assert protocol_automation.status in acceptable_automation_task_statuses, (
            f"AutomationState.status is {protocol_automation.status.value!r}; "
            f"expected one of {[status.value for status in acceptable_automation_task_statuses]!r}"
        )
    elif expected_automation_task_status is not None:
        assert protocol_automation.status == expected_automation_task_status, (
            f"AutomationState.status is {protocol_automation.status.value!r}; "
            f"expected {expected_automation_task_status.value!r}"
        )
    buy_orders, sell_orders, flow_trade_count = buy_sell_trade_counts_from_exchange_elements(
        exchange_account_elements,
    )
    expected_open_count = buy_orders + sell_orders
    protocol_orders = protocol_automation.orders or []
    protocol_trades = protocol_automation.trades or []
    assert len(protocol_orders) == expected_open_count, (
        f"protocol open order count {len(protocol_orders)} != flow open orders {expected_open_count} "
        f"(buy={buy_orders}, sell={sell_orders})"
    )
    assert len(protocol_trades) == flow_trade_count, (
        f"protocol trade count {len(protocol_trades)} != flow trade count {flow_trade_count}"
    )
    for order_summary in protocol_orders:
        assert order_summary.symbol in allowed_order_symbols, (
            f"unexpected OrderSummary.symbol {order_summary.symbol!r}; "
            f"expected one of {allowed_order_symbols!r}"
        )
    content = portfolio_content_from_exchange_elements(exchange_account_elements)
    protocol_assets = protocol_automation.assets
    assert protocol_assets is not None, "expected AutomationState.assets to be set"
    assets_by_symbol = {asset.symbol: asset for asset in protocol_assets}
    for symbol, row in content.items():
        matching_asset = assets_by_symbol.get(symbol)
        assert matching_asset is not None, (
            f"missing protocol Asset for portfolio symbol {symbol!r}; "
            f"protocol asset symbols: {sorted(assets_by_symbol)!r}"
        )
        expected_total = portfolio_row_scalar(row, "total")
        expected_available = portfolio_row_scalar(row, "available")
        if not math.isclose(float(matching_asset.total), expected_total, rel_tol=1e-9, abs_tol=1e-6):
            raise AssertionError(
                f"Asset.total mismatch for {symbol!r}: protocol={matching_asset.total!r} "
                f"flow={expected_total!r}"
            )
        if not math.isclose(float(matching_asset.available), expected_available, rel_tol=1e-9, abs_tol=1e-6):
            raise AssertionError(
                f"Asset.available mismatch for {symbol!r}: protocol={matching_asset.available!r} "
                f"flow={expected_available!r}"
            )
