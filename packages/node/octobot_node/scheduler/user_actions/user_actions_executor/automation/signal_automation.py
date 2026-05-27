#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import typing

import octobot_protocol.models as protocol_models

import octobot_flow.entities
import octobot_node.errors as node_errors
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_node.scheduler.user_actions.user_actions_executor.automation.automation_user_action_executor as automation_user_action_executor


def _get_signal_automation_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.SignalAutomationConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete signal-automation configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.SignalAutomationConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"SignalAutomationActionExecutor expected SignalAutomationConfiguration, "
            f"got {type(payload).__name__}"
        )
    return payload


def _raw_signal_payload(
    signal_config: protocol_models.SignalAutomationConfiguration,
) -> typing.Any:
    if signal_config.signal_payload is None:
        return None
    return signal_config.signal_payload.to_dict()


def _parse_actions_payload(raw_payload: typing.Any) -> list[dict]:
    if raw_payload is None:
        raise node_errors.InvalidUserActionPayloadError(
            "signal_payload is required for actions signal_type."
        )
    if isinstance(raw_payload, list):
        if not raw_payload:
            raise node_errors.InvalidUserActionPayloadError(
                "signal_payload actions list must not be empty."
            )
        if not all(isinstance(action, dict) for action in raw_payload):
            raise node_errors.InvalidUserActionPayloadError(
                "signal_payload actions list must contain only action dicts."
            )
        return raw_payload
    if isinstance(raw_payload, dict):
        nested_actions = raw_payload.get("actions")
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
        return [raw_payload]
    raise node_errors.InvalidUserActionPayloadError(
        f"signal_payload for actions must be a list or dict, got {type(raw_payload).__name__}."
    )


def _parse_trading_signal_payload(raw_payload: typing.Any) -> octobot_flow.entities.TradingSignal:
    if raw_payload is None:
        raise node_errors.InvalidUserActionPayloadError(
            "signal_payload is required for trading_signal signal_type."
        )
    if isinstance(raw_payload, list):
        if len(raw_payload) != 1 or not isinstance(raw_payload[0], dict):
            raise node_errors.InvalidUserActionPayloadError(
                "signal_payload for trading_signal must be a single trading-signal dict or a one-element list."
            )
        return octobot_flow.entities.TradingSignal.from_dict(raw_payload[0])
    if isinstance(raw_payload, dict):
        return octobot_flow.entities.TradingSignal.from_dict(raw_payload)
    raise node_errors.InvalidUserActionPayloadError(
        f"signal_payload for trading_signal must be a dict or one-element list, got {type(raw_payload).__name__}."
    )


async def _resolve_target_automation_workflow_id(
    parent_automation_id: str,
    wallet_address: str,
) -> str:
    scheduler = scheduler_module.SCHEDULER
    matching_workflow_ids = await scheduler.resolve_active_automation_workflow_ids_for_parent_id(
        wallet_address,
        parent_automation_id,
    )
    if not matching_workflow_ids:
        raise node_errors.ActiveAutomationWorkflowNotFoundError(
            f"No active automation workflow for parent id {parent_automation_id!r} "
            f"(wallet_address={wallet_address!r})."
        )
    if len(matching_workflow_ids) > 1:
        raise node_errors.AmbiguousActiveAutomationWorkflowError(
            f"Expected exactly one active automation workflow for parent id {parent_automation_id!r}, "
            f"got {len(matching_workflow_ids)}: {matching_workflow_ids!r} "
            f"(wallet_address={wallet_address!r})."
        )
    return matching_workflow_ids[0]


async def _send_actions_to_automation_with_workflow_lookup(
    actions: list[dict],
    automation_id: str,
    wallet_address: str,
) -> None:
    target_workflow_id = await _resolve_target_automation_workflow_id(automation_id, wallet_address)
    await scheduler_tasks.send_actions_to_automation_workflow(actions, target_workflow_id)


async def _send_forced_trigger_to_automation_with_workflow_lookup(
    automation_id: str,
    wallet_address: str,
) -> None:
    target_workflow_id = await _resolve_target_automation_workflow_id(automation_id, wallet_address)
    await scheduler_tasks.send_forced_trigger_to_automation_workflow(target_workflow_id)


class SignalAutomationActionExecutor(automation_user_action_executor.AutomationUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        if not scheduler_module.is_initialized():
            raise RuntimeError("Scheduler is not initialized")

        signal_config = _get_signal_automation_payload(user_action)
        raw_payload = _raw_signal_payload(signal_config)

        match signal_config.signal_type:
            case protocol_models.AutomationSignalType.ACTIONS:
                actions = _parse_actions_payload(raw_payload)
                await _send_actions_to_automation_with_workflow_lookup(
                    actions,
                    signal_config.automation_id,
                    self._wallet_address,
                )
            case protocol_models.AutomationSignalType.TRADING_SIGNAL:
                trading_signal = _parse_trading_signal_payload(raw_payload)
                await scheduler_tasks.trigger_copier_automation(
                    signal_config.automation_id,
                    trading_signal,
                )
            case protocol_models.AutomationSignalType.FORCED_TRIGGER:
                await _send_forced_trigger_to_automation_with_workflow_lookup(
                    signal_config.automation_id,
                    self._wallet_address,
                )
            case _:
                raise node_errors.InvalidUserActionPayloadError(
                    f"Unsupported signal_type: {signal_config.signal_type!r}"
                )

        self._mark_user_action_completed(user_action)
