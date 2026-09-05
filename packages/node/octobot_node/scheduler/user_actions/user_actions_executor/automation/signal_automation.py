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

import dbos

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.user_actions.signal_priority_action as signal_priority_action_module
import octobot_node.scheduler.user_actions.user_actions_executor.automation.automation_user_action_executor as automation_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_priority_action_builder as signal_priority_action_builder
import octobot_flow.entities


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


def _should_await_signal_execution(
    actions: list[signal_priority_action_module.SignalPriorityAction],
) -> bool:
    return any(action.await_execution_result for action in actions)


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
                actions = await signal_priority_action_builder.build_signal_priority_actions(
                    user_action_id=user_action.id,
                    automation_id=signal_config.automation_id,
                    user_id=self._user_id,
                    signal_payload=raw_payload,
                )
                action_dicts = [
                    action.to_dict(include_default_values=False) for action in actions
                ]
                if _should_await_signal_execution(actions):
                    reply_workflow_id = dbos.DBOS.workflow_id
                    if reply_workflow_id is None:
                        raise RuntimeError(
                            "Missing current workflow ID while dispatching signal priority actions."
                        )
                    execution_result_callback = workflow_params.AutomationWorkflowExecutionResultCallback(
                        reply_workflow_id=reply_workflow_id,
                        user_action_id=user_action.id,
                    )
                    await scheduler_tasks.send_actions_to_active_automation(
                        signal_config.automation_id,
                        self._user_id,
                        action_dicts,
                        execution_result_callback,
                    )
                    self.signal_execution_await_context = workflow_params.SignalExecutionAwaitContext(
                        user_action_id=user_action.id,
                        sent_action_ids=[action.id for action in actions],
                    )
                else:
                    await scheduler_tasks.send_actions_to_active_automation(
                        signal_config.automation_id,
                        self._user_id,
                        action_dicts,
                    )
                    self._mark_user_action_completed(user_action)
            case protocol_models.AutomationSignalType.TRADING_SIGNAL:
                trading_signal = _parse_trading_signal_payload(raw_payload)
                await scheduler_tasks.trigger_copier_automation(
                    signal_config.automation_id,
                    trading_signal,
                )
                self._mark_user_action_completed(user_action)
            case protocol_models.AutomationSignalType.FORCED_TRIGGER:
                await scheduler_tasks.send_forced_trigger_to_active_automation(
                    signal_config.automation_id,
                    self._user_id,
                )
                self._mark_user_action_completed(user_action)
            case _:
                raise node_errors.InvalidUserActionPayloadError(
                    f"Unsupported signal_type: {signal_config.signal_type!r}"
                )
