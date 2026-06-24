#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Generic-process OctoBot automation helpers for DBOS functional tests."""

from __future__ import annotations

import asyncio
import datetime
import time
import typing
import uuid

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models_module
import pytest

from . import workflow_common as workflow_common_module

GENERIC_PROCESS_DEFAULT_STRATEGY_ID = "functional-generic-process-default-strategy"
GENERIC_PROCESS_ACTION_ID = f"{protocol_models_module.ActionConfigurationType.GENERIC_PROCESS.value}_1"
GLOBAL_INIT_TIMEOUT_SEC = 60.0
INIT_POLL_INTERVAL_SEC = 2.0
CHILD_STOP_WAIT_SEC = 20.0


def build_generic_process_configuration(
    *,
    profile_data: dict[str, typing.Any] | None = None,
) -> protocol_models_module.GenericProcessConfiguration:
    configuration_fields: dict[str, typing.Any] = {
        "configuration_type": protocol_models_module.ActionConfigurationType.GENERIC_PROCESS,
    }
    if profile_data is not None:
        configuration_fields["profile_data"] = profile_data
    return protocol_models_module.GenericProcessConfiguration(**configuration_fields)


def seeded_generic_process_strategy_for_functional_wallet(
    *,
    stored_strategy_id: str = GENERIC_PROCESS_DEFAULT_STRATEGY_ID,
    profile_data: dict[str, typing.Any] | None = None,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Generic process automation strategy",
        reference_market="USDC",
        configuration=protocol_models_module.StrategyConfiguration(
            build_generic_process_configuration(profile_data=profile_data),
        ),
    )


def build_create_strategy_user_action(
    *,
    strategy_id: str = GENERIC_PROCESS_DEFAULT_STRATEGY_ID,
    profile_data: dict[str, typing.Any] | None = None,
) -> protocol_models_module.UserAction:
    strategy = seeded_generic_process_strategy_for_functional_wallet(
        stored_strategy_id=strategy_id,
        profile_data=profile_data,
    )
    strategy_payload = protocol_models_module.CreateStrategyConfiguration(
        action_type=protocol_models_module.UserActionType.STRATEGY_CREATE,
        configuration=strategy,
    )
    return protocol_models_module.UserAction(
        id=f"ua-strategy-create-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(strategy_payload),
    )


def build_create_exchange_config_user_action(
    *,
    exchange_config_id: str = "functional-generic-process-exchange-config",
) -> protocol_models_module.UserAction:
    payload = protocol_models_module.CreateExchangeConfigConfiguration(
        action_type=protocol_models_module.UserActionType.EXCHANGE_CONFIG_CREATE,
        configuration=protocol_models_module.ExchangeConfig(
            id=exchange_config_id,
            name="binance-main",
            exchange=workflow_common_module.exchange_internal_name(),
            sandboxed=False,
        ),
    )
    return protocol_models_module.UserAction(
        id=f"ua-exchange-config-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )


def build_create_account_user_action(
    *,
    account_id: str,
    exchange_config_id: str = "functional-generic-process-exchange-config",
) -> protocol_models_module.UserAction:
    payload = protocol_models_module.CreateAccountConfiguration(
        action_type=protocol_models_module.UserActionType.ACCOUNT_CREATE,
        configuration=protocol_models_module.Account(
            id=account_id,
            name="Functional generic process account",
            is_simulated=True,
            created_at=datetime.datetime(2026, 6, 1, 10, 0, 0, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 6, 1, 10, 0, 0, tzinfo=datetime.UTC),
            assets=[
                protocol_models_module.DetailedAssetsForTradingType(
                    trading_type=protocol_models_module.TradingType.SPOT,
                    assets=[
                        protocol_models_module.DetailedAsset(
                            symbol="USDC",
                            total=1000.0,
                            available=1000.0,
                        )
                    ],
                )
            ],
            specifics=protocol_models_module.AccountSpecifics(
                actual_instance=protocol_models_module.ExchangeAccount(
                    account_type=protocol_models_module.AccountType.EXCHANGE,
                    remote_account_id=account_id,
                    exchange_config_ids=[exchange_config_id],
                ),
            ),
        ),
    )
    return protocol_models_module.UserAction(
        id=f"ua-account-create-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )


def build_create_generic_process_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str = GENERIC_PROCESS_DEFAULT_STRATEGY_ID,
    automation_id: str | None = None,
) -> protocol_models_module.UserAction:
    strategy_reference = protocol_models_module.StrategyReference(
        id=strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
    )
    automation_configuration_fields: dict[str, typing.Any] = {
        "name": name,
        "created_at": datetime.datetime(2026, 6, 1, 11, 0, 0, tzinfo=datetime.UTC),
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
        id=f"ua-generic-process-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )


def _recall_inner_state(run_result: typing.Optional[dict]) -> typing.Optional[dict]:
    if not isinstance(run_result, dict):
        return None
    recalling_payload = run_result.get(dsl_interpreter.ReCallingOperatorResult.__name__)
    if not isinstance(recalling_payload, dict):
        return None
    inner_state = recalling_payload.get("last_execution_result")
    return inner_state if isinstance(inner_state, dict) else None


def recall_inner_from_run_octobot_action(
    action: flow_entities.AbstractActionDetails,
) -> typing.Optional[dict]:
    for run_result in (action.result, action.previous_execution_result):
        inner_state = _recall_inner_state(run_result) if run_result is not None else None
        if inner_state is not None:
            return inner_state
    return None


def get_action_by_id(
    automation_state: flow_entities.AutomationState,
    action_id: str,
) -> typing.Optional[flow_entities.AbstractActionDetails]:
    for action in automation_state.automation.actions_dag.actions:
        if action.id == action_id:
            return action
    return None


async def wait_for_init_state_ok(
    scheduler: typing.Any,
    automation_id: str,
    *,
    timeout_sec: float = GLOBAL_INIT_TIMEOUT_SEC,
    poll_interval_sec: float = INIT_POLL_INTERVAL_SEC,
) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        workflow_rows = await scheduler.INSTANCE.list_workflows_async()
        for workflow_row in workflow_rows:
            import octobot_node.scheduler.workflows_util as workflows_util_module

            if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                continue
            state_reader = workflows_util_module.get_automation_state_reader(workflow_row)
            if state_reader is None:
                continue
            run_action = get_action_by_id(state_reader.state, GENERIC_PROCESS_ACTION_ID)
            if run_action is None:
                continue
            inner_state = recall_inner_from_run_octobot_action(run_action)
            if inner_state and inner_state.get("init_state_ok") is True:
                return inner_state
        await asyncio.sleep(poll_interval_sec)
    pytest.fail(f"Timed out waiting for init_state_ok on {GENERIC_PROCESS_ACTION_ID!r} within {timeout_sec}s")
