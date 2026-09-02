#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.

import typing

import dbos

import octobot_commons.constants as commons_constants
import octobot_flow.entities.signals.signal_exchange_context as signal_exchange_context_module
import octobot_flow.errors as flow_errors
import octobot_flow.parsers.signal_script_resolver as signal_script_resolver
import octobot_trading.enums as trading_enums
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_node.errors as node_errors
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
import octobot_node.scheduler as scheduler_module


def normalize_signal_payload(signal_payload: typing.Any) -> list[dict]:
    if signal_payload is None:
        raise node_errors.InvalidUserActionPayloadError(
            "signal_payload is required for actions signal_type."
        )
    if isinstance(signal_payload, list):
        if not signal_payload:
            raise node_errors.InvalidUserActionPayloadError(
                "signal_payload actions list must not be empty."
            )
        if not all(isinstance(action, dict) for action in signal_payload):
            raise node_errors.InvalidUserActionPayloadError(
                "signal_payload actions list must contain only action dicts."
            )
        return signal_payload
    if isinstance(signal_payload, dict):
        nested_actions = signal_payload.get("actions")
        if nested_actions is not None:
            if not isinstance(nested_actions, list) or not all(
                isinstance(action, dict) for action in nested_actions
            ):
                raise node_errors.InvalidUserActionPayloadError(
                    "signal_payload.actions must be a list of action dicts."
                )
            if not nested_actions:
                raise node_errors.InvalidUserActionPayloadError(
                    "signal_payload.actions must not be empty."
                )
            return nested_actions
        return [signal_payload]
    raise node_errors.InvalidUserActionPayloadError(
        f"signal_payload for actions must be a list or dict, got {type(signal_payload).__name__}."
    )


def _exchange_type_from_flow_state(flow_automation_state) -> typing.Optional[trading_enums.ExchangeTypes]:
    exchange_account_details = flow_automation_state.exchange_account_details
    if exchange_account_details is None:
        return None
    exchange_type_value = exchange_account_details.exchange_details.exchange_type
    protocol_trading_type = commons_constants.EXCHANGE_TYPE_TO_TRADING_TYPE.get(exchange_type_value)
    if protocol_trading_type is None:
        return None
    return protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(protocol_trading_type)


async def _load_signal_exchange_context(
    *,
    automation_id: str,
    user_id: str,
) -> signal_exchange_context_module.SignalExchangeContext:
    active_workflow_ids = await scheduler_module.SCHEDULER.resolve_active_automation_workflow_ids_for_parent_id(
        user_id,
        automation_id,
    )
    if not active_workflow_ids:
        raise node_errors.ActiveAutomationWorkflowNotFoundError(
            f"No active automation workflow for parent id {automation_id!r} "
            f"(user_id={user_id!r})."
        )
    if len(active_workflow_ids) > 1:
        raise node_errors.AmbiguousActiveAutomationWorkflowError(
            f"Expected exactly one active automation workflow for parent id {automation_id!r}, "
            f"got {len(active_workflow_ids)}: {active_workflow_ids!r} "
            f"(user_id={user_id!r})."
        )
    flow_states_by_id = await automation_states_loader.load_flow_automation_states_by_id(
        user_id,
        statuses=[
            dbos.WorkflowStatusString.ENQUEUED,
            dbos.WorkflowStatusString.PENDING,
        ],
    )
    flow_automation_state = flow_states_by_id.get(automation_id)
    if flow_automation_state is None or flow_automation_state.exchange_account_details is None:
        raise node_errors.ActiveAutomationWorkflowNotFoundError(
            f"No active automation exchange context for parent id {automation_id!r} "
            f"(user_id={user_id!r})."
        )
    exchange_account_details = flow_automation_state.exchange_account_details
    return signal_exchange_context_module.SignalExchangeContext(
        exchange_name=exchange_account_details.exchange_details.internal_name,
        exchange_type=_exchange_type_from_flow_state(flow_automation_state),
        reference_market=exchange_account_details.portfolio.unit or None,
        ignore_exchange_key=True,
    )


def _default_priority_action_id(user_action_id: str, signal_index: int) -> str:
    return f"action_signal_priority_{user_action_id}_{signal_index}"


def _resolve_signal_to_priority_action(
    *,
    signal: dict,
    signal_index: int,
    user_action_id: str,
    exchange_context: signal_exchange_context_module.SignalExchangeContext,
) -> dict:
    if "script" in signal:
        try:
            dsl_script = signal_script_resolver.resolve_signal_script(
                signal["script"],
                exchange_name=exchange_context.exchange_name,
                exchange_type=exchange_context.exchange_type,
                reference_market=exchange_context.reference_market,
                ignore_exchange_key=exchange_context.ignore_exchange_key,
            )
        except flow_errors.InvalidAutomationActionError as error:
            raise node_errors.InvalidUserActionPayloadError(str(error)) from error
        action_id = signal.get("id") or _default_priority_action_id(user_action_id, signal_index)
        return {"id": action_id, "dsl_script": dsl_script}

    if signal_script_resolver.signal_key() in signal:
        try:
            dsl_script = signal_script_resolver.resolve_signal_script(
                signal,
                exchange_name=exchange_context.exchange_name,
                exchange_type=exchange_context.exchange_type,
                reference_market=exchange_context.reference_market,
                ignore_exchange_key=exchange_context.ignore_exchange_key,
            )
        except flow_errors.InvalidAutomationActionError as error:
            raise node_errors.InvalidUserActionPayloadError(str(error)) from error
        action_id = signal.get("id") or _default_priority_action_id(user_action_id, signal_index)
        return {"id": action_id, "dsl_script": dsl_script}

    if "dsl_script" in signal and "script" not in signal:
        return signal

    raise node_errors.InvalidUserActionPayloadError(
        f"Unsupported signal payload shape at index {signal_index}: {signal!r}"
    )


async def build_signal_priority_actions(
    *,
    user_action_id: str,
    automation_id: str,
    user_id: str,
    signal_payload: typing.Any,
) -> list[dict]:
    normalized_signals = normalize_signal_payload(signal_payload)
    exchange_context = await _load_signal_exchange_context(
        automation_id=automation_id,
        user_id=user_id,
    )
    priority_actions: list[dict] = []
    for signal_index, signal in enumerate(normalized_signals):
        priority_actions.append(
            _resolve_signal_to_priority_action(
                signal=signal,
                signal_index=signal_index,
                user_action_id=user_action_id,
                exchange_context=exchange_context,
            )
        )
    return priority_actions
