#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Shared helpers for grid and DCA simulator automation DBOS functional tests."""

from __future__ import annotations

import asyncio
import datetime
import json
import time
import typing

import dbos
import pytest

import octobot_sync.chain.evm as sync_evm_module
import octobot_sync.server as sync_server_module
import octobot_trading.constants as trading_constants_module
import octobot_trading.enums as trading_enums_module

import octobot_node.constants as node_constants_module
import octobot_node.scheduler
import octobot_node.scheduler.workflows
import octobot_node.scheduler.api as scheduler_api_module
import octobot_node.scheduler.workflows.params as workflow_params_module
import octobot_node.scheduler.workflows_util as workflows_util_module
import octobot_protocol.models as protocol_models_module

# Passphrase for grid functional tests (WalletBackend requires length >= 8).
SIMULATOR_GRID_TEST_WALLET_PASSPHRASE = "simgridPW1!"

SIMULATOR_GRID_TEST_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)
SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS = sync_evm_module.address_from_evm_key(
    SIMULATOR_GRID_TEST_PRIVATE_KEY
).lower()
SIMULATOR_GRID_TEST_COMMUNITY_USER_ID = sync_server_module.derive_user_id(
    SIMULATOR_GRID_TEST_PRIVATE_KEY
)

DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS = DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS

_FUNCTIONAL_PROTOCOL_ACCOUNT_TS = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)
SIMULATOR_FUNCTIONAL_STRATEGY_VERSION = "1.0.0"


def exchange_internal_name() -> str:
    return "binanceus"


def wrap_user_action_configuration(payload) -> protocol_models_module.UserActionConfiguration:
    return protocol_models_module.UserActionConfiguration.from_json(payload.to_json())


def protocol_exchange_config_for_grid_functional() -> protocol_models_module.ExchangeConfig:
    return protocol_models_module.ExchangeConfig(
        id="functional-test-exchange-config-id",
        name="binance-main",
        exchange=exchange_internal_name(),
        sandboxed=False,
    )


def protocol_exchange_account_for_grid_functional(
    *,
    usdc_total: float,
    remote_account_id: str,
) -> protocol_models_module.ExchangeAccount:
    return protocol_models_module.ExchangeAccount(
        account_type=protocol_models_module.AccountType.EXCHANGE,
        remote_account_id=remote_account_id,
        exchange_config_ids=["functional-test-exchange-config-id"],
    )


def protocol_account_for_functional(
    *,
    account_id: str,
    usdc_total: float,
    account_name: str = "Functional test account",
) -> protocol_models_module.Account:
    return protocol_models_module.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        updated_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        assets=[
            protocol_models_module.DetailedAssetsForTradingType(
                trading_type=protocol_models_module.TradingType.SPOT,
                assets=[
                    protocol_models_module.DetailedAsset(
                        symbol="USDC",
                        total=usdc_total,
                        available=usdc_total,
                    )
                ],
            )
        ],
        specifics=protocol_models_module.AccountSpecifics(
            actual_instance=protocol_exchange_account_for_grid_functional(
                usdc_total=usdc_total,
                remote_account_id=account_id,
            ),
        ),
    )


def build_stop_user_action(
    *,
    automation_id: str,
    user_action_id: str,
) -> protocol_models_module.UserAction:
    payload = protocol_models_module.StopAutomationConfiguration(
        action_type=protocol_models_module.UserActionType.AUTOMATION_STOP,
        id=automation_id,
    )
    return protocol_models_module.UserAction(
        id=user_action_id,
        configuration=wrap_user_action_configuration(payload),
    )


def build_forced_trigger_signal_user_action(
    *,
    automation_id: str,
    user_action_id: str,
) -> protocol_models_module.UserAction:
    payload = protocol_models_module.SignalAutomationConfiguration(
        action_type=protocol_models_module.UserActionType.AUTOMATION_SIGNAL,
        automation_id=automation_id,
        signal_type=protocol_models_module.AutomationSignalType.FORCED_TRIGGER,
    )
    return protocol_models_module.UserAction(
        id=user_action_id,
        configuration=wrap_user_action_configuration(payload),
    )


def parse_automation_workflow_output(
    workflow_output: str,
) -> workflow_params_module.AutomationWorkflowOutput:
    payload = json.loads(workflow_output)
    return workflow_params_module.AutomationWorkflowOutput.from_dict(payload)


def job_description_dict_from_output(
    parsed: workflow_params_module.AutomationWorkflowOutput,
) -> dict[str, typing.Any]:
    assert isinstance(parsed.state, str)
    return json.loads(parsed.state)


def buy_sell_trade_counts_from_exchange_elements(
    exchange_account_elements: typing.Any,
) -> tuple[int, int, int]:
    if exchange_account_elements is None:
        return 0, 0, 0
    orders_container = getattr(exchange_account_elements, "orders", None)
    if orders_container is None and isinstance(exchange_account_elements, dict):
        orders_container = exchange_account_elements.get("orders")
    if orders_container is None:
        trades_only = getattr(exchange_account_elements, "trades", None)
        if trades_only is None and isinstance(exchange_account_elements, dict):
            trades_only = exchange_account_elements.get("trades", [])
        return 0, 0, len(trades_only or [])

    open_orders = getattr(orders_container, "open_orders", None)
    if open_orders is None and isinstance(orders_container, dict):
        open_orders = orders_container.get("open_orders", [])
    open_orders = open_orders or []

    side_key = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
    storage_key = trading_constants_module.STORAGE_ORIGIN_VALUE
    buy_count = 0
    sell_count = 0
    for order in open_orders:
        if isinstance(order, dict):
            inner = order.get(storage_key, {})
        else:
            inner = getattr(order, storage_key, {})
        side = inner.get(side_key) if isinstance(inner, dict) else getattr(inner, side_key, None)
        if side == trading_enums_module.TradeOrderSide.BUY.value:
            buy_count += 1
        elif side == trading_enums_module.TradeOrderSide.SELL.value:
            sell_count += 1

    trades = getattr(exchange_account_elements, "trades", None)
    if trades is None and isinstance(exchange_account_elements, dict):
        trades = exchange_account_elements.get("trades", [])
    trade_count = len(trades or [])
    return buy_count, sell_count, trade_count


def find_protocol_automation_state(
    automation_states: list[protocol_models_module.AutomationState],
    parent_workflow_id: str,
) -> typing.Optional[protocol_models_module.AutomationState]:
    normalized_id = parent_workflow_id[: node_constants_module.PARENT_WORKFLOW_ID_LENGTH]
    for automation in automation_states:
        if automation.id == normalized_id:
            return automation
    return None


async def load_protocol_automation_state_for_workflow(
    user_id: typing.Optional[str],
    workflow_row: dbos.WorkflowStatus,
) -> protocol_models_module.AutomationState:
    parent_id = workflow_row.workflow_id[: node_constants_module.PARENT_WORKFLOW_ID_LENGTH]
    automation_states = await scheduler_api_module.get_automation_states(user_id)
    automation_state = find_protocol_automation_state(automation_states, parent_id)
    if automation_state is None:
        seen_ids = [automation.id for automation in automation_states]
        raise AssertionError(
            f"No AutomationState entry for parent_workflow_id={parent_id!r}; "
            f"returned automation ids: {seen_ids!r}"
        )
    return automation_state


async def wait_for_stop_success_output(
    scheduler,
    automation_id: str,
    deadline_seconds: float,
    *,
    poll_interval_seconds: float = DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS,
) -> str:
    stop_deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < stop_deadline:
        workflow_rows = await scheduler.INSTANCE.list_workflows_async()
        for workflow_row in workflow_rows:
            if workflow_row.status != dbos.WorkflowStatusString.SUCCESS.value:
                continue
            if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                continue
            workflow_handle = await scheduler.INSTANCE.retrieve_workflow_async(workflow_row.workflow_id)
            result_text = await workflow_handle.get_result()
            if not result_text:
                continue
            parsed_output = parse_automation_workflow_output(result_text)
            if parsed_output.error:
                continue
            job_dict = job_description_dict_from_output(parsed_output)
            automation_payload = job_dict["state"]["automation"]
            if automation_payload.get("post_actions", {}).get("stop_automation"):
                return result_text
        await asyncio.sleep(poll_interval_seconds)
    pytest.fail(f"Timed out waiting for stop completion for {automation_id}")


async def enqueue_forced_trigger_and_await(
    scheduler: typing.Any,
    *,
    automation_id: str,
    user_id: str,
    user_action_id: str,
    timeout_seconds: float = 10.0,
) -> protocol_models_module.UserAction:
    signal_user_action = build_forced_trigger_signal_user_action(
        automation_id=automation_id,
        user_action_id=user_action_id,
    )
    try:
        await asyncio.wait_for(
            enqueue_user_action_workflow_and_await_terminal_result(
                scheduler,
                signal_user_action,
                user_id,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise AssertionError(
            f"execute_user_action forced-trigger signal timed out for {user_action_id!r}"
        ) from exc
    return signal_user_action


async def enqueue_user_action_workflow_and_await_terminal_result(
    scheduler: typing.Any,
    user_action_bundle: typing.Any,
    user_id: str,
):
    """``execute_user_action`` queues user actions; wait until the USER_ACTION_QUEUE workflow completes."""
    import octobot_node.scheduler.tasks as scheduler_tasks_module

    workflow_identifier_encoded = await scheduler_tasks_module.trigger_user_action_workflow(
        user_action_bundle,
        user_id,
    )
    terminal_handle_encoded = await scheduler.INSTANCE.retrieve_workflow_async(workflow_identifier_encoded)
    await terminal_handle_encoded.get_result()
