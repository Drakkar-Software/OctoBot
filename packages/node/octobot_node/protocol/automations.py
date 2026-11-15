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
import octobot_flow.entities.automations.octobot_process_state as octobot_process_state_module
import octobot_node.models as node_models
import octobot_node.protocol.accounts as accounts_protocol
import octobot_node.protocol.accounts_trading as accounts_trading_protocol
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers.user_account_provider as user_account_provider
import octobot_trading.constants as octobot_trading_constants
import octobot_trading.enums as octobot_trading_enums
import octobot_trading.personal_data.portfolios.protocol as octobot_trading_portfolios_protocol
import octobot_node.protocol.util.privacy_filter as privacy_filter


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
            # cloud be InvalidAutomationActionError when dag parsing fails
            task = source.task
            content_preview = octobot_commons_logging.get_private_minimized_message_if_necessary(
                (task.content or "")[:80] if isinstance(task.content, str) else repr(task.content)
            )
            logger.debug(
                f"Skipping malformed automation task id={task.id!r}: {exc} ({exc.__class__.__name__}) "
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


def _degraded_state_protocol_errors(
    execution: flow_entities.ExecutionDetails,
) -> tuple[typing.Optional[str], typing.Optional[str]]:
    degraded_state = execution.degraded_state
    if degraded_state.since <= 0 or not degraded_state.error:
        return None, None
    return degraded_state.error, degraded_state.reason


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
    if error is None and error_message is None:
        error, error_message = filled.error, filled.error_message
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
    if content_missing:
        flow_automation_state = _empty_flow_automation_state()
    else:
        import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
        flow_automation_state = automation_states_loader.parse_flow_automation_state(task)
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
        configuration = privacy_filter.protocol_action_configuration(
            flow_action.config,
            action_type=flow_action.action,
        )
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


def _octobot_process_state_to_child_protocol(
    state: octobot_process_state_module.OctobotProcessState,
) -> protocol_models.ChildOctoBotProcessState:
    """Project full recall state → slim API shape for task cards."""
    return protocol_models.ChildOctoBotProcessState(
        http_base_url=state.http_base_url,
        web_port=state.web_port,
        init_state_ok=state.init_state_ok,
    )


def _child_octobot_process_from_flow_actions(
    actions: typing.Iterable[flow_entities.AbstractActionDetails],
) -> protocol_models.ChildOctoBotProcessState | None:
    """Find run_octobot_process recall on DAG actions and map to protocol child state."""
    for flow_action in actions:
        if not isinstance(flow_action, flow_entities.DSLScriptActionDetails):
            continue
        if not octobot_process_state_module.is_run_octobot_process_dsl_action(flow_action):
            continue
        action_result = flow_action.result
        if action_result is None:
            action_result = flow_action.previous_execution_result
        inner = octobot_process_state_module.recall_inner_from_action_result(action_result)
        if parsed_state := octobot_process_state_module.parse_octobot_process_state(inner or {}):
            return _octobot_process_state_to_child_protocol(parsed_state)
    return None


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
    assets: typing.Optional[list[protocol_models.DetailedAssetsForTradingType]] = None
    orders: typing.Optional[list[protocol_models.OrderSummary]] = None
    trades: typing.Optional[list[protocol_models.TradeSummary]] = None
    positions: typing.Optional[list[protocol_models.PositionSummary]] = None
    if exchange_elements:
        portfolio = exchange_elements.portfolio
        positions = _position_summaries(exchange_elements.positions) or None
        if portfolio.content:
            detailed_assets = octobot_trading_portfolios_protocol.to_protocol_assets(portfolio.content)
            if detailed_assets:
                trading_type = (
                    protocol_models.TradingType.FUTURES
                    if exchange_elements.positions
                    else protocol_models.TradingType.SPOT
                )
                assets = [
                    protocol_models.DetailedAssetsForTradingType(
                        trading_type=trading_type,
                        assets=detailed_assets,
                    )
                ]
        orders = _order_summaries_from_open_orders(exchange_elements.orders.open_orders) or None
        trades = _automation_trade_summaries(exchange_elements) or None
    metadata = protocol_automation_state.metadata.model_copy(
        update={
            "updated_at": _metadata_updated_at_from_execution(
                flow_automation_state.automation.execution
            ),
        }
    )
    degraded_error, degraded_error_message = _degraded_state_protocol_errors(
        flow_automation_state.automation.execution
    )
    child_octobot_process = _child_octobot_process_from_flow_actions(
        actions_dag.actions
    )
    return protocol_automation_state.model_copy(
        update={
            "status": status,
            "error": degraded_error,
            "error_message": degraded_error_message,
            "metadata": metadata,
            "actions": dag_actions or None,
            "priority_actions": priority_actions or None,
            "exchanges": exchanges,
            "exchange_account_ids": exchange_account_ids,
            "assets": assets,
            "orders": orders,
            "trades": trades,
            "positions": positions,
            "child_octobot_process": child_octobot_process,
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


def _automation_trade_summaries(
    exchange_elements: flow_entities.ExchangeAccountElements,
) -> list[protocol_models.TradeSummary]:
    summaries_by_id: dict[str, protocol_models.TradeSummary] = {}
    for symbol, trade_ids in (exchange_elements.trade_summaries or {}).items():
        symbol_text = str(symbol).strip()
        if not symbol_text:
            continue
        for trade_id in trade_ids or []:
            trade_id_text = str(trade_id).strip()
            if not trade_id_text:
                continue
            summaries_by_id[trade_id_text] = protocol_models.TradeSummary(
                id=trade_id_text,
                symbol=symbol_text,
            )
    for trade_summary in _trade_summaries(exchange_elements.trades):
        summaries_by_id[trade_summary.id] = trade_summary
    return list(summaries_by_id.values())


def wallet_account_ids(
    accounts: list[protocol_models.Account] | None,
) -> list[str]:
    if not accounts:
        return []
    return [
        account.id
        for account in accounts
        if account.id
    ]


def fees_by_currency_from_trades(
    trades: list[protocol_models.Trade],
) -> dict[str, float]:
    fees: dict[str, float] = {}
    for trade in trades:
        if trade.fee is None:
            continue
        currency = trade.fee.currency
        fees[currency] = fees.get(currency, 0.0) + float(trade.fee.amount)
    return fees


@dataclasses.dataclass(frozen=True)
class AutomationReadView:
    user_id: str
    automation: protocol_models.AutomationState
    orders: list[protocol_models.Order]
    trades: list[protocol_models.Trade]
    fees_by_currency: dict[str, float]

    @property
    def display_name(self) -> str:
        name = self.automation.metadata.name
        return name if name else self.automation.id


def _trading_by_account_id(
    account_tradings: list[protocol_models.AccountTradingWithAccountId] | None,
) -> dict[str, protocol_models.AccountTrading]:
    trading_by_id: dict[str, protocol_models.AccountTrading] = {}
    if not account_tradings:
        return trading_by_id
    for entry in account_tradings:
        if entry.account_id and entry.account_trading is not None:
            trading_by_id[entry.account_id] = entry.account_trading
    return trading_by_id


def _running_automation_states(
    automations: list[protocol_models.AutomationState],
) -> list[protocol_models.AutomationState]:
    return [
        automation for automation in automations
        if automation.status is protocol_models.WorkflowStatus.RUNNING
    ]


def _orders_bound_to_automation(
    automation: protocol_models.AutomationState,
    account_orders: list[protocol_models.Order],
) -> list[protocol_models.Order]:
    bound_ids = {summary.id for summary in (automation.orders or [])}
    if not bound_ids:
        return []
    return [
        order for order in account_orders
        if order.id in bound_ids or order.exchange_id in bound_ids
    ]


def _trades_bound_to_automation(
    automation: protocol_models.AutomationState,
    account_trades: list[protocol_models.Trade],
) -> list[protocol_models.Trade]:
    bound_ids = {summary.id for summary in (automation.trades or [])}
    if not bound_ids:
        return []
    return [
        trade for trade in account_trades
        if trade.trade_id in bound_ids or trade.id in bound_ids
    ]


def _build_view_for_automation(
    user_id: str,
    automation: protocol_models.AutomationState,
    trading_by_account_id: dict[str, protocol_models.AccountTrading],
) -> AutomationReadView:
    account_ids = automation.exchange_account_ids or []
    orders: list[protocol_models.Order] = []
    trades: list[protocol_models.Trade] = []
    for account_id in account_ids:
        trading = trading_by_account_id.get(account_id)
        if trading is None:
            continue
        if trading.orders:
            orders.extend(trading.orders)
        if trading.trades:
            trades.extend(trading.trades)
    bound_orders = _orders_bound_to_automation(automation, orders)
    bound_trades = _trades_bound_to_automation(automation, trades)
    return AutomationReadView(
        user_id=user_id,
        automation=automation,
        orders=bound_orders,
        trades=bound_trades,
        fees_by_currency=fees_by_currency_from_trades(bound_trades),
    )


async def get_automation_read_views(
    user_ids: list[str] | None = None,
) -> list[AutomationReadView]:
    if user_ids is None:
        user_ids = user_account_provider.AccountProvider.instance().list_collectable_wallet_ids()
    views: list[AutomationReadView] = []
    for user_id in user_ids:
        automations = await scheduler_api.get_automation_states(
            user_id,
            statuses=list(automation_states_loader.ACTIVE_AUTOMATION_STATUSES),
        )
        automations = _running_automation_states(automations)
        account_state = accounts_protocol.get_accounts_state(user_id)
        account_tradings = accounts_trading_protocol.get_account_trading_summaries(
            user_id,
            wallet_account_ids(account_state.accounts),
        )
        trading_by_account_id = _trading_by_account_id(account_tradings)
        for automation in automations:
            views.append(_build_view_for_automation(user_id, automation, trading_by_account_id))
    return views
