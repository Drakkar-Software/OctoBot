#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Helpers for outdated-reference-account copy automation functional tests."""

from __future__ import annotations

import asyncio
import decimal
import time
import typing

import dbos
import pytest

import octobot_commons.timestamp_util as timestamp_util
import octobot_copy.constants as copy_constants
import octobot_flow.entities as octobot_flow_entities
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals_module
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

from . import exchange_account_elements_access as exchange_account_elements_access_module
from . import grid_workflow as grid_workflow_module
from . import workflow_common as workflow_common_module

FRESH_MARKET_PRICE = 110_000.0
STALE_ORDER_PRICE = 67_326.0
FRESH_ORDER_PRICE = FRESH_MARKET_PRICE * 0.99
MASTER_STRATEGY_ID = "functional-outdated-reference-master-strategy"
COPY_AUTOMATION_ID = "d4e5f6a7-b8c9-4901-d234-567890abcdef"
COPY_ACCOUNT_ID = "functional_outdated_reference_copy_account"
OUTDATED_SKIP_LOG_SUBSTRING = "Outdated reference account, skipping copy iteration"
_BTC_USDC = "BTC/USDC"


def _open_limit_order(
    *,
    order_id: str,
    price: float,
    side: protocol_models.Side = protocol_models.Side.SELL,
    trigger_above: bool = True,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol=_BTC_USDC,
        price=price,
        quantity=0.001,
        filled=0.0,
        exchange_id=f"exchange-{order_id}",
        side=side,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=trigger_above,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _copied_account(*, orders: list[protocol_models.Order]) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=1_710_000_000.0,
        copied_assets=[
            protocol_models.CopiedAsset(name="USDC", total=1000.0, available=1000.0, ratio=0.5),
            protocol_models.CopiedAsset(name="BTC", total=0.01, available=0.01, ratio=0.5),
        ],
        orders=orders,
    )


def build_stale_trading_signal() -> octobot_flow_entities.TradingSignal:
    return octobot_flow_entities.TradingSignal(
        strategy_id=MASTER_STRATEGY_ID,
        account=_copied_account(
            orders=[_open_limit_order(order_id="stale-order", price=STALE_ORDER_PRICE, trigger_above=True)],
        ),
    )


def build_fresh_trading_signal() -> octobot_flow_entities.TradingSignal:
    return octobot_flow_entities.TradingSignal(
        strategy_id=MASTER_STRATEGY_ID,
        account=_copied_account(
            orders=[_open_limit_order(order_id="fresh-order", price=FRESH_ORDER_PRICE, trigger_above=True)],
        ),
    )


def build_create_copy_follower_user_action() -> protocol_models.UserAction:
    return grid_workflow_module.build_create_copy_follower_user_action(
        automation_id=COPY_AUTOMATION_ID,
        account_id=COPY_ACCOUNT_ID,
        name="test_outdated_reference_copy_follower",
        strategy_id=MASTER_STRATEGY_ID,
    )


def caplog_contains_outdated_skip(caplog) -> bool:
    return any(
        OUTDATED_SKIP_LOG_SUBSTRING in record.getMessage()
        for record in caplog.records
    )


async def deliver_trading_signal_when_pending(
    scheduler: typing.Any,
    automation_id: str,
    trading_signal: octobot_flow_entities.TradingSignal,
    deadline_seconds: float,
) -> None:
    poll_interval = 0.05
    poll_deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < poll_deadline:
        pending_rows = await scheduler.INSTANCE.list_workflows_async(
            status=[
                dbos.WorkflowStatusString.ENQUEUED.value,
                dbos.WorkflowStatusString.PENDING.value,
            ],
        )
        for workflow_row in pending_rows:
            if automation_states_loader_module.get_automation_id(workflow_row) != automation_id:
                continue
            copied_strategy_ids = automation_states_loader_module.get_automation_copied_strategy_ids(workflow_row)
            if trading_signal.strategy_id not in copied_strategy_ids:
                continue
            await internal_trading_signals_module.send_internal_trading_signal(trading_signal)
            return
        await asyncio.sleep(poll_interval)
    pytest.fail(
        f"Timed out delivering trading signal for automation_id={automation_id!r} "
        f"strategy_id={trading_signal.strategy_id!r}"
    )


def sell_limit_prices_from_reader(state_reader: typing.Any) -> list[decimal.Decimal]:
    return exchange_account_elements_access_module.sorted_open_limit_prices_from_elements(
        state_reader.state.automation.exchange_account_elements,
        trade_order_side=trading_enums.TradeOrderSide.SELL,
    )


async def poll_state_reader_until(
    scheduler: typing.Any,
    automation_id: str,
    predicate: typing.Callable[[typing.Any], bool],
    deadline_seconds: float,
    failure_label: str,
) -> typing.Any:
    poll_interval = workflow_common_module.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS
    poll_deadline = time.monotonic() + deadline_seconds
    last_reader: typing.Any = None
    while time.monotonic() < poll_deadline:
        workflow_rows = await scheduler.INSTANCE.list_workflows_async()
        for workflow_row in workflow_rows:
            if automation_states_loader_module.get_automation_id(workflow_row) != automation_id:
                continue
            state_reader = automation_states_loader_module.get_automation_state_reader(workflow_row)
            if state_reader is None:
                continue
            last_reader = state_reader
            if predicate(state_reader):
                return state_reader
        await asyncio.sleep(poll_interval)
    detail = "no reader"
    if last_reader is not None:
        sell_prices = sell_limit_prices_from_reader(last_reader)
        detail = f"last sell limit prices={sell_prices!s}"
    pytest.fail(f"Timed out waiting for {failure_label} ({detail})")
