#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import datetime
import typing
import uuid

import octobot_protocol.models as protocol_models

import octobot_node.constants
import octobot_node.errors as node_errors
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers


def _wrap_user_action_configuration(
    payload: typing.Any,
) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(payload.to_json())


def _build_non_trading_generic_process_octobot_strategy() -> protocol_models.Strategy:
    generic_process_configuration = protocol_models.GenericProcessConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
    )
    return protocol_models.Strategy(
        id=octobot_node.constants.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
        version=octobot_node.constants.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_VERSION,
        name="Generic process OctoBot strategy",
        reference_market="USDC",
        configuration=protocol_models.StrategyConfiguration(generic_process_configuration),
    )


def _build_create_strategy_user_action(
    strategy: protocol_models.Strategy,
) -> protocol_models.UserAction:
    strategy_payload = protocol_models.CreateStrategyConfiguration(
        action_type=protocol_models.UserActionType.STRATEGY_CREATE,
        configuration=strategy,
    )
    return protocol_models.UserAction(
        id=f"ua-strategy-create-{uuid.uuid4()}",
        configuration=_wrap_user_action_configuration(strategy_payload),
    )


def _build_create_automation_user_action(
    *,
    automation_user_action_id: str,
    name: str,
    strategy: protocol_models.Strategy,
) -> protocol_models.UserAction:
    strategy_reference = protocol_models.StrategyReference(
        id=strategy.id,
        version=strategy.version,
        emit_signals=False,
    )
    automation_configuration = protocol_models.AutomationConfiguration(
        id=automation_user_action_id,
        name=name,
        created_at=datetime.datetime.now(datetime.UTC),
        strategy=strategy_reference,
        accounts=[],
    )
    automation_payload = protocol_models.CreateAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
        configuration=automation_configuration,
    )
    return protocol_models.UserAction(
        id=automation_user_action_id,
        configuration=_wrap_user_action_configuration(automation_payload),
    )


def _updated_user_action_from_workflow_result(
    workflow_result: typing.Any,
) -> protocol_models.UserAction:
    if isinstance(workflow_result, str):
        workflow_result = workflow_params.UserActionWorkflowOutput.from_json(workflow_result)
    elif isinstance(workflow_result, dict):
        workflow_result = workflow_params.UserActionWorkflowOutput.from_dict(workflow_result)
    elif not isinstance(workflow_result, workflow_params.UserActionWorkflowOutput):
        raise node_errors.UserActionError(
            f"Unexpected user action workflow result type: {type(workflow_result).__name__}"
        )
    updated_user_action = workflow_result.updated_user_action
    if updated_user_action.status == protocol_models.UserActionStatus.FAILED:
        error_details = None
        if updated_user_action.result and updated_user_action.result.actual_instance:
            error_details = getattr(
                updated_user_action.result.actual_instance,
                "error_details",
                None,
            )
        raise node_errors.UserActionError(
            error_details or f"User action {updated_user_action.id!r} failed"
        )
    if updated_user_action.status != protocol_models.UserActionStatus.COMPLETED:
        raise node_errors.UserActionError(
            f"User action {updated_user_action.id!r} finished with status "
            f"{updated_user_action.status!r}, expected completed"
        )
    return updated_user_action


def _created_automation_id_from_user_action(
    updated_user_action: protocol_models.UserAction,
) -> str:
    if updated_user_action.result is None or updated_user_action.result.actual_instance is None:
        raise node_errors.UserActionError(
            f"Automation create user action {updated_user_action.id!r} has no result"
        )
    automation_result = updated_user_action.result.actual_instance
    if not isinstance(automation_result, protocol_models.AutomationActionResult):
        raise node_errors.UserActionError(
            f"Automation create user action {updated_user_action.id!r} returned "
            f"{type(automation_result).__name__}, expected AutomationActionResult"
        )
    if not automation_result.created_automation_id:
        raise node_errors.UserActionError(
            f"Automation create user action {updated_user_action.id!r} has no created_automation_id"
        )
    return automation_result.created_automation_id


async def _execute_user_action_and_await(
    user_id: str,
    user_action: protocol_models.UserAction,
) -> protocol_models.UserAction:
    workflow_id = await scheduler_tasks.trigger_user_action_workflow(user_action, user_id)
    workflow_result = await scheduler_api.await_workflow_result_from_id(workflow_id)
    return _updated_user_action_from_workflow_result(workflow_result)


async def _ensure_non_trading_generic_process_octobot_strategy(
    user_id: str,
) -> protocol_models.Strategy:
    strategy_provider = collection_providers.StrategyProvider.instance()
    try:
        return strategy_provider.get_item(
            user_id,
            octobot_node.constants.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
        )
    except collection_errors.ItemNotFoundError:
        strategy = _build_non_trading_generic_process_octobot_strategy()
        create_strategy_user_action = _build_create_strategy_user_action(strategy)
        await _execute_user_action_and_await(user_id, create_strategy_user_action)
        return strategy_provider.get_item(
            user_id,
            octobot_node.constants.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
        )


async def create_generic_process_bot(
    user_id: str,
    name: str,
    automation_id: str | None = None,
) -> str:
    stored_strategy = await _ensure_non_trading_generic_process_octobot_strategy(user_id)
    resolved_automation_id = automation_id or str(uuid.uuid4())
    create_automation_user_action = _build_create_automation_user_action(
        automation_user_action_id=resolved_automation_id,
        name=name,
        strategy=stored_strategy,
    )
    updated_user_action = await _execute_user_action_and_await(
        user_id,
        create_automation_user_action,
    )
    return _created_automation_id_from_user_action(updated_user_action)
