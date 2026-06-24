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

import dataclasses
import datetime
import enum
import json
import typing

import dbos
import octobot_commons.logging as octobot_commons_logging
import octobot_commons.timestamp_util as octobot_commons_timestamp_util
import octobot_flow.entities as flow_entities
import octobot_node.models as node_models
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_protocol.models as protocol_models
import octobot_trading.constants as octobot_trading_constants
import octobot_trading.enums as octobot_trading_enums
import octobot_trading.personal_data.portfolios.protocol as octobot_trading_portfolios_protocol


logger = octobot_commons_logging.get_logger("AutomationsProtocol")


@dataclasses.dataclass
class AutomationStateSource:
    task: node_models.Task
    workflow_status: str
    workflow_output: typing.Optional[workflow_params.AutomationWorkflowOutput] = None
    workflow_error: typing.Optional[str] = None


def to_protocol_automations_state(
    sources: list[AutomationStateSource],
) -> list[protocol_models.AutomationState]:
    states: list[protocol_models.AutomationState] = []
    for source in sources:
        try:
            states.append(_to_protocol_automation_state(
                source.task,
                workflow_status=source.workflow_status,
                workflow_output=source.workflow_output,
                workflow_error=source.workflow_error,
            ))
        except Exception as exc:
            task = source.task
            content_preview = (task.content or "")[:80] if isinstance(task.content, str) else repr(task.content)
            logger.warning(
                f"Skipping malformed automation task id={task.id!r}: {exc} "
                f"(content_metadata={task.content_metadata!r}, content_preview={content_preview!r})"
            )
    return states


def _resolve_automation_status(
    flow_status: protocol_models.WorkflowStatus,
    workflow_status: str,
    workflow_output: typing.Optional[workflow_params.AutomationWorkflowOutput],
) -> protocol_models.WorkflowStatus:
    active_statuses = (
        dbos.WorkflowStatusString.ENQUEUED.value,
        dbos.WorkflowStatusString.PENDING.value,
    )
    if workflow_status in active_statuses:
        return flow_status
    if workflow_status == dbos.WorkflowStatusString.CANCELLED.value:
        return protocol_models.WorkflowStatus.CANCELED
    if workflow_status in (
        dbos.WorkflowStatusString.ERROR.value,
        dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED.value,
    ):
        return protocol_models.WorkflowStatus.FAILED
    if workflow_status == dbos.WorkflowStatusString.SUCCESS.value:
        if workflow_output is not None and workflow_output.error:
            return protocol_models.WorkflowStatus.FAILED
        if flow_status == protocol_models.WorkflowStatus.FAILED:
            return protocol_models.WorkflowStatus.FAILED
        return protocol_models.WorkflowStatus.COMPLETED
    if flow_status in (protocol_models.WorkflowStatus.FAILED, protocol_models.WorkflowStatus.CANCELED):
        return flow_status
    return protocol_models.WorkflowStatus.COMPLETED


def _resolve_automation_errors(
    workflow_status: str,
    workflow_output: typing.Optional[workflow_params.AutomationWorkflowOutput],
    workflow_error: typing.Optional[str],
) -> tuple[typing.Optional[str], typing.Optional[str]]:
    if workflow_status == dbos.WorkflowStatusString.SUCCESS.value:
        if workflow_output is not None and workflow_output.error:
            return workflow_output.error, workflow_output.error_message
        return None, None
    if workflow_status in (
        dbos.WorkflowStatusString.ERROR.value,
        dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED.value,
    ):
        return workflow_error or "Execution failed", None
    return None, None


def _task_content_is_missing(content: typing.Optional[str]) -> bool:
    return content is None or content == ""


def _empty_flow_automation_state() -> flow_entities.AutomationState:
    return flow_entities.AutomationState(
        automation=flow_entities.AutomationDetails(
            metadata=flow_entities.AutomationMetadata(automation_id=""),
            actions_dag=flow_entities.ActionsDAG(actions=[]),
        ),
    )


def _merge_task_errors_when_workflow_errors_absent(
    task: node_models.Task,
    workflow_error: typing.Optional[str],
    workflow_error_message: typing.Optional[str],
) -> tuple[typing.Optional[str], typing.Optional[str]]:
    if workflow_error is not None or workflow_error_message is not None:
        return workflow_error, workflow_error_message
    return task.error, task.error_message


def _base_protocol_automation_state(task: node_models.Task) -> protocol_models.AutomationState:
    return protocol_models.AutomationState(
        id=task.id,
        status=protocol_models.WorkflowStatus.PENDING,
        metadata=protocol_models.AutomationMetadata(
            name=task.name or "",
            description="",
        ),
    )


def _apply_workflow_resolution_to_automation_state(
    filled: protocol_models.AutomationState,
    task: node_models.Task,
    *,
    workflow_status: str,
    workflow_output: typing.Optional[workflow_params.AutomationWorkflowOutput],
    workflow_error: typing.Optional[str],
    merge_task_errors_when_workflow_absent: bool,
) -> protocol_models.AutomationState:
    resolved_status = _resolve_automation_status(
        filled.status, workflow_status, workflow_output
    )
    resolved_error, resolved_error_message = _resolve_automation_errors(
        workflow_status, workflow_output, workflow_error
    )
    if merge_task_errors_when_workflow_absent:
        error, error_message = _merge_task_errors_when_workflow_errors_absent(
            task, resolved_error, resolved_error_message
        )
    else:
        error, error_message = resolved_error, resolved_error_message
    return filled.model_copy(update={
        "status": resolved_status,
        "error": error,
        "error_message": error_message,
    })


def _to_protocol_automation_state(
    task: node_models.Task,
    *,
    workflow_status: str,
    workflow_output: typing.Optional[workflow_params.AutomationWorkflowOutput] = None,
    workflow_error: typing.Optional[str] = None,
) -> protocol_models.AutomationState:
    content_missing = _task_content_is_missing(task.content)
    flow_automation_state = (
        _empty_flow_automation_state()
        if content_missing
        else _parse_automation_state(task)
    )
    filled = _fill_protocol_automation_state(
        _base_protocol_automation_state(task), flow_automation_state
    )
    return _apply_workflow_resolution_to_automation_state(
        filled,
        task,
        workflow_status=workflow_status,
        workflow_output=workflow_output,
        workflow_error=workflow_error,
        merge_task_errors_when_workflow_absent=content_missing,
    )


def _parse_automation_state(task: node_models.Task) -> flow_entities.AutomationState:
    parsed_description = octobot_flow_client.OctoBotActionsJobDescription.parse_task_description(task.content)
    automation_state: octobot_flow_client.OctoBotActionsJobDescription = octobot_flow_client.OctoBotActionsJobDescription.from_dict(
        parsed_description
    )
    return flow_entities.AutomationState.from_dict(automation_state.state)


def _flow_action_reports_error(flow_action: flow_entities.AbstractActionDetails) -> bool:
    error_status = flow_action.error_status
    if error_status is None:
        return False
    if isinstance(error_status, enum.Enum):
        return error_status.value is not None
    return bool(error_status)


def _flow_error_status_to_protocol_str(error_status: typing.Any) -> typing.Optional[str]:
    if error_status is None:
        return None
    if isinstance(error_status, enum.Enum):
        raw_value = error_status.value
        if raw_value is None:
            return None
        return str(raw_value)
    return str(error_status)


def _flow_result_to_protocol_str(result: typing.Any) -> typing.Optional[str]:
    if result is None:
        return None
    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)


def _flow_action_result_for_protocol(
    flow_action: flow_entities.AbstractActionDetails,
) -> typing.Any:
    if flow_action.result is not None:
        return flow_action.result
    return flow_action.previous_execution_result


def _metadata_updated_at_from_execution(
    execution: flow_entities.ExecutionDetails,
) -> typing.Optional[datetime.datetime]:
    execution_timestamps = (
        execution.previous_execution.triggered_at,
        execution.current_execution.triggered_at,
    )
    positive_timestamps = [
        timestamp for timestamp in execution_timestamps if timestamp > 0
    ]
    if not positive_timestamps:
        return None
    latest_timestamp = max(positive_timestamps)
    return octobot_commons_timestamp_util.utc_datetime_from_timestamp(latest_timestamp)


def _automation_task_status(flow_automation_state: flow_entities.AutomationState) -> protocol_models.WorkflowStatus:
    execution = flow_automation_state.automation.execution
    actions_dag = flow_automation_state.automation.actions_dag
    post_actions = flow_automation_state.automation.post_actions
    if execution.execution_error:
        return protocol_models.WorkflowStatus.FAILED
    if any(_flow_action_reports_error(action) for action in actions_dag.actions):
        return protocol_models.WorkflowStatus.FAILED
    if actions_dag.completed_all_actions() or post_actions.stop_automation:
        return protocol_models.WorkflowStatus.COMPLETED
    if (
        execution.current_execution.triggered_at > 0
        or execution.previous_execution.triggered_at > 0
        or any(action.is_completed() for action in actions_dag.actions)
    ):
        return protocol_models.WorkflowStatus.RUNNING
    return protocol_models.WorkflowStatus.PENDING


def _protocol_action_from_flow(
    flow_action: flow_entities.AbstractActionDetails,
    *,
    priority_lane: bool,
    executable_ids: typing.Optional[set[str]],
) -> protocol_models.Action:
    if _flow_action_reports_error(flow_action):
        action_status = protocol_models.WorkflowStatus.FAILED
    elif flow_action.is_completed():
        action_status = protocol_models.WorkflowStatus.COMPLETED
    elif priority_lane:
        action_status = protocol_models.WorkflowStatus.RUNNING
    else:
        if executable_ids is None:
            raise ValueError(
                "executable_ids is required when priority_lane is False."
            )
        action_status = (
            protocol_models.WorkflowStatus.RUNNING
            if flow_action.id in executable_ids
            else protocol_models.WorkflowStatus.PENDING
        )
    if isinstance(flow_action, flow_entities.DSLScriptActionDetails):
        action_type = "dsl_script"
        dsl_value = flow_action.resolved_dsl_script or flow_action.dsl_script
        configuration = None
    elif isinstance(flow_action, flow_entities.ConfiguredActionDetails):
        action_type = flow_action.action
        dsl_value = None
        configuration = flow_action.config
    else:
        raise TypeError(f"Unsupported flow action type: {type(flow_action).__name__}")
    completed_at = None
    if flow_action.executed_at is not None:
        completed_at = octobot_commons_timestamp_util.utc_datetime_from_timestamp(flow_action.executed_at)
    return protocol_models.Action(
        id=flow_action.id,
        action_type=action_type,
        status=action_status,
        dsl=dsl_value,
        configuration=configuration,
        result=_flow_result_to_protocol_str(_flow_action_result_for_protocol(flow_action)),
        error=_flow_error_status_to_protocol_str(flow_action.error_status),
        completed_at=completed_at,
    )


def _fill_protocol_automation_state(
    protocol_automation_state: protocol_models.AutomationState,
    flow_automation_state: flow_entities.AutomationState,
) -> protocol_models.AutomationState:
    # Resolve automation status and map DAG / priority actions to protocol actions.
    status = _automation_task_status(flow_automation_state)
    actions_dag = flow_automation_state.automation.actions_dag
    executable_ids = {action.id for action in actions_dag.get_executable_actions()}
    dag_actions = [
        _protocol_action_from_flow(action, priority_lane=False, executable_ids=executable_ids)
        for action in actions_dag.actions
    ]
    priority_actions: typing.Optional[list[protocol_models.Action]] = None
    if flow_automation_state.priority_actions:
        priority_actions = [
            _protocol_action_from_flow(priority_action, priority_lane=True, executable_ids=None)
            for priority_action in flow_automation_state.priority_actions
        ]
    # Attach exchange identifiers when account details exist on the flow state.
    exchange_details = flow_automation_state.exchange_account_details
    exchanges: typing.Optional[list[str]] = None
    exchange_account_ids: typing.Optional[list[str]] = None
    if exchange_details:
        internal_name = exchange_details.exchange_details.internal_name
        if internal_name:
            exchanges = [internal_name]
        bound_account_id = exchange_details.exchange_details.exchange_account_id
        if bound_account_id:
            exchange_account_ids = [bound_account_id]
    # Derive portfolio and trading summaries from automation exchange elements.
    exchange_elements = flow_automation_state.automation.exchange_account_elements
    assets: typing.Optional[list[protocol_models.DetailedAsset]] = None
    orders: typing.Optional[list[protocol_models.OrderSummary]] = None
    trades: typing.Optional[list[protocol_models.TradeSummary]] = None
    positions: typing.Optional[list[protocol_models.PositionSummary]] = None
    if exchange_elements:
        portfolio = exchange_elements.portfolio
        if portfolio.content:
            assets = octobot_trading_portfolios_protocol.to_protocol_assets(portfolio.content)
        orders = _order_summaries_from_open_orders(exchange_elements.orders.open_orders) or None
        positions = _position_summaries(exchange_elements.positions) or None
        trades = _trade_summaries(exchange_elements.trades) or None
    metadata = protocol_automation_state.metadata.model_copy(
        update={
            "updated_at": _metadata_updated_at_from_execution(
                flow_automation_state.automation.execution
            ),
        }
    )
    return protocol_automation_state.model_copy(
        update={
            "status": status,
            "metadata": metadata,
            "actions": dag_actions or None,
            "priority_actions": priority_actions or None,
            "exchanges": exchanges,
            "exchange_account_ids": exchange_account_ids,
            "assets": assets,
            "orders": orders,
            "trades": trades,
            "positions": positions,
        }
    )


def _order_summaries_from_open_orders(open_orders: list[dict]) -> list[protocol_models.OrderSummary]:
    order_columns = octobot_trading_enums.ExchangeConstantsOrderColumns
    summaries: list[protocol_models.OrderSummary] = []
    for order in open_orders:
        inner = order.get(octobot_trading_constants.STORAGE_ORIGIN_VALUE, order)
        if not isinstance(inner, dict):
            inner = order
        order_id = inner.get(order_columns.EXCHANGE_ID.value) or inner.get(order_columns.ID.value)
        symbol = inner.get(order_columns.SYMBOL.value)
        if order_id is None or symbol is None:
            continue
        summaries.append(protocol_models.OrderSummary(id=str(order_id), symbol=str(symbol)))
    return summaries


def _position_summaries(positions: list[typing.Any]) -> list[protocol_models.PositionSummary]:
    position_columns = octobot_trading_enums.ExchangeConstantsPositionColumns
    summaries: list[protocol_models.PositionSummary] = []
    for position_details in positions:
        position_dict = position_details.position
        position_id = position_dict.get(position_columns.ID.value)
        symbol = position_dict.get(position_columns.SYMBOL.value)
        if position_id is None or symbol is None:
            continue
        summaries.append(protocol_models.PositionSummary(id=str(position_id), symbol=str(symbol)))
    return summaries


def _trade_summaries(trades: list[dict]) -> list[protocol_models.TradeSummary]:
    order_columns = octobot_trading_enums.ExchangeConstantsOrderColumns
    summaries: list[protocol_models.TradeSummary] = []
    for trade in trades:
        trade_id = trade.get(order_columns.EXCHANGE_TRADE_ID.value) or trade.get(order_columns.EXCHANGE_ID.value)
        symbol = trade.get(order_columns.SYMBOL.value)
        if trade_id is None or symbol is None:
            continue
        summaries.append(protocol_models.TradeSummary(id=str(trade_id), symbol=str(symbol)))
    return summaries
