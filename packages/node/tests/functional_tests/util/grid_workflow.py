#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Grid-specific helpers for simulator automation DBOS functional tests."""

from __future__ import annotations

import datetime
import uuid

import octobot_protocol.models as protocol_models_module

from . import workflow_common as workflow_common_module

GRID_INCREMENT = 200
GRID_SPREAD = 600
FIXED_BTC_USDC_CLOSE = 100000.0

SIMULATOR_GRID_DEFAULT_STRATEGY_ID = "simulator-grid-functional-default-strategy"
SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID = "simulator-functional-copy-stored-strategy"


def seeded_grid_strategy_for_functional_wallet(
    *,
    stored_strategy_id: str,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Simulator grid automation strategy",
        reference_market="USDC",
        configuration=protocol_models_module.StrategyConfiguration(
            grid_configuration_matching_simulator_constants(),
        ),
    )


def seeded_copy_follower_strategy_for_functional_wallet(
    *,
    copy_master_strategy_id: str,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Simulator copy-follower automation strategy",
        reference_market="USDC",
        configuration=protocol_models_module.StrategyConfiguration(
            protocol_models_module.CopyConfiguration(
                configuration_type=protocol_models_module.ActionConfigurationType.COPY,
                strategy_id=copy_master_strategy_id,
            )
        ),
    )


def grid_configuration_matching_simulator_constants() -> protocol_models_module.GridConfiguration:
    return protocol_models_module.GridConfiguration(
        configuration_type=protocol_models_module.ActionConfigurationType.GRID,
        symbol="BTC/USDC",
        spread=GRID_SPREAD,
        increment=GRID_INCREMENT,
        buy_count=2,
        sell_count=2,
        enable_trailing_up=False,
        enable_trailing_down=False,
        order_by_order_trailing=False,
    )


def build_create_grid_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str | None = None,
    emit_signals: bool | None = None,
) -> protocol_models_module.UserAction:
    reference_strategy_identifier = strategy_id or SIMULATOR_GRID_DEFAULT_STRATEGY_ID
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
        id=f"ua-grid-{uuid.uuid4()}",
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )


def build_create_copy_follower_user_action(
    *,
    automation_id: str,
    account_id: str,
    name: str,
    strategy_id: str,
) -> protocol_models_module.UserAction:
    strategy_reference = protocol_models_module.StrategyReference(
        id=SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
    )
    automation_configuration = protocol_models_module.AutomationConfiguration(
        name=name,
        created_at=datetime.datetime(2026, 5, 10, 8, 1, 0, tzinfo=datetime.UTC),
        strategy=strategy_reference,
        accounts=[protocol_models_module.AccountReference(id=account_id)],
    )
    payload = protocol_models_module.CreateAutomationConfiguration(
        action_type=protocol_models_module.UserActionType.AUTOMATION_CREATE,
        configuration=automation_configuration,
    )
    return protocol_models_module.UserAction(
        id=automation_id,
        configuration=workflow_common_module.wrap_user_action_configuration(payload),
    )


def is_simulator_grid_baseline_exactly_one_trade(buy_count: int, sell_count: int, trade_count: int) -> bool:
    return buy_count == 2 and sell_count == 2 and trade_count == 1


def is_simulator_grid_baseline_at_least_one_trade(buy_count: int, sell_count: int, trade_count: int) -> bool:
    return buy_count == 2 and sell_count == 2 and trade_count >= 1
