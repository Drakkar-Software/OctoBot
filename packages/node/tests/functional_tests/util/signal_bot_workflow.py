#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
"""Signal-bot helpers for simulator automation DBOS functional tests."""

from __future__ import annotations

import asyncio
import datetime
import time
import typing
import uuid

import dbos
import pytest

import octobot_protocol.models as protocol_models_module
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module

from . import workflow_common as workflow_common_module

SIMULATOR_SIGNAL_BOT_DEFAULT_STRATEGY_ID = "simulator-signal-bot-functional-default-strategy"


def signal_bot_configuration_for_functional() -> protocol_models_module.SignalBotConfiguration:
    return protocol_models_module.SignalBotConfiguration(
        configuration_type=protocol_models_module.ActionConfigurationType.SIGNAL_BOT,
        sync_interval_with_open_trades_seconds=5.0,
        sync_interval_without_open_trades_seconds=10.0,
    )


def seeded_signal_bot_strategy_for_functional_wallet(
    *,
    stored_strategy_id: str,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Simulator signal bot automation strategy",
        reference_market="USDC",
        configuration=protocol_models_module.StrategyConfiguration(
            signal_bot_configuration_for_functional(),
        ),
    )


async def wait_for_signal_exchange_context_ready(
    scheduler: typing.Any,
    automation_id: str,
    user_id: str,
    deadline_seconds: float,
) -> None:
    poll_deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < poll_deadline:
        active_workflow_ids = await scheduler.resolve_active_automation_workflow_ids_for_parent_id(
            user_id,
            automation_id,
        )
        if not active_workflow_ids:
            await asyncio.sleep(workflow_common_module.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS)
            continue
        flow_states_by_id = await automation_states_loader_module.load_flow_automation_states_by_id(
            user_id,
            statuses=[
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
        )
        flow_automation_state = flow_states_by_id.get(automation_id)
        if flow_automation_state is not None and flow_automation_state.exchange_account_details is not None:
            return
        await asyncio.sleep(workflow_common_module.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"Timed out waiting for signal bot exchange context for {automation_id!r} "
        f"within {deadline_seconds}s"
    )


def build_create_signal_bot_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str | None = None,
    automation_id: str | None = None,
) -> protocol_models_module.UserAction:
    reference_strategy_identifier = strategy_id or SIMULATOR_SIGNAL_BOT_DEFAULT_STRATEGY_ID
    strategy_reference = protocol_models_module.StrategyReference(
        id=reference_strategy_identifier,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        emit_signals=False,
    )
    automation_configuration_fields = {
        "name": name,
        "created_at": datetime.datetime(2026, 5, 10, 8, 0, 0, tzinfo=datetime.UTC),
        "strategy": strategy_reference,
        "accounts": [protocol_models_module.AccountReference(id=account_id)],
    }
    if automation_id is not None:
        automation_configuration_fields["id"] = automation_id
    automation_configuration = protocol_models_module.AutomationConfiguration(
        **automation_configuration_fields,
    )
    payload = protocol_models_module.CreateAutomationConfiguration(
        action_type=protocol_models_module.UserActionType.AUTOMATION_CREATE,
        configuration=automation_configuration,
    )
    return protocol_models_module.UserAction(
        id=f"ua-signal-bot-{uuid.uuid4()}",
        status=protocol_models_module.UserActionStatus.PENDING,
        created_at=datetime.datetime(2026, 5, 10, 8, 0, 0, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 5, 10, 8, 0, 0, tzinfo=datetime.UTC),
        configuration=protocol_models_module.UserActionConfiguration.from_json(payload.to_json()),
    )
