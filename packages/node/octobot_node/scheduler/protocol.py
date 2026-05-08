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

import enum
import json
import typing

import octobot_commons.timestamp_util as octobot_commons_timestamp_util
import octobot_flow.entities as flow_entities
import octobot_node.constants as node_constants
import octobot_node.models as node_models
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_protocol.models as protocol_models
import octobot_trading.enums as octobot_trading_enums
import octobot_trading.personal_data.portfolios.protocol as octobot_trading_portfolios_protocol
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

def to_protocol_accounts_state(automation_states: list[flow_entities.AutomationState]) -> protocol_models.AccountsState:
    return protocol_models.AccountsState(
        version=node_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
        accounts=_to_protocol_accounts_from_automation_states(automation_states)
    )


def to_protocol_automations_state(tasks: list[node_models.Task]) -> protocol_models.AutomationsState:
    return protocol_models.AutomationsState(
        version=node_constants.AUTOMATIONS_STATE_VERSION,
        automations=[_to_protocol_automation_state(task) for task in tasks]
    )


def _to_protocol_accounts_from_automation_states(automation_states: list[flow_entities.AutomationState]) -> list[protocol_models.Account]:
    accounts = []
    for automation_state in automation_states:
        if account := _to_protocol_account_from_automation_state(automation_state):
            accounts.append(account)
    return accounts

def _to_protocol_account_from_automation_state(automation_state: flow_entities.AutomationState) -> typing.Optional[protocol_models.Account]:
    if not automation_state.exchange_account_details:
        return None
    return protocol_models.Account(
        id=automation_state.exchange_account_details.metadata.id,
        account_type=protocol_models.AccountType.EXCHANGE,
        name=automation_state.exchange_account_details.metadata.name,
        is_simulated=automation_state.exchange_account_details.is_simulated(),
    )

def _to_protocol_automation_state(task: node_models.Task) -> protocol_models.AutomationState:
    flow_automation_state = _parse_automation_state(task)
    protocol_automation_state = protocol_models.AutomationState(
        id=task.id,
        status=protocol_models.TaskStatus.PENDING,
        metadata=protocol_models.AutomationMetadata(
            name=task.name or "",
            description="",
        ),
    )
    return _fill_protocol_automation_state(protocol_automation_state, flow_automation_state)


def _parse_automation_state(task: node_models.Task) -> flow_entities.AutomationState:
    parsed_description = octobot_flow_client.OctoBotActionsJobDescription.parse_task_description(task.content)
    automation_state: octobot_flow_client.OctoBotActionsJobDescription = octobot_flow_client.OctoBotActionsJobDescription.from_dict(
        parsed_description
    )
    return flow_entities.AutomationState.from_dict(automation_state)


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


def _automation_task_status(flow_automation_state: flow_entities.AutomationState) -> protocol_models.TaskStatus:
    execution = flow_automation_state.automation.execution
    actions_dag = flow_automation_state.automation.actions_dag
    if execution.execution_error:
        return protocol_models.TaskStatus.FAILED
    if any(_flow_action_reports_error(action) for action in actions_dag.actions):
        return protocol_models.TaskStatus.FAILED
    if actions_dag.completed_all_actions():
        return protocol_models.TaskStatus.COMPLETED
    if execution.current_execution.triggered_at > 0 or any(action.is_completed() for action in actions_dag.actions):
        return protocol_models.TaskStatus.RUNNING
    return protocol_models.TaskStatus.PENDING


def _protocol_action_from_flow(
    flow_action: flow_entities.AbstractActionDetails,
    *,
    priority_lane: bool,
    executable_ids: typing.Optional[set[str]],
) -> protocol_models.Action:
    if _flow_action_reports_error(flow_action):
        action_status = protocol_models.TaskStatus.FAILED
    elif flow_action.is_completed():
        action_status = protocol_models.TaskStatus.COMPLETED
    elif priority_lane:
        action_status = protocol_models.TaskStatus.RUNNING
    else:
        if executable_ids is None:
            raise ValueError("executable_ids is required when priority_lane is False")
        action_status = (
            protocol_models.TaskStatus.RUNNING
            if flow_action.id in executable_ids
            else protocol_models.TaskStatus.PENDING
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
        result=_flow_result_to_protocol_str(flow_action.result),
        error=_flow_error_status_to_protocol_str(flow_action.error_status),
        completed_at=completed_at,
    )


def _enrich_protocol_assets(
    base_assets: list[protocol_models.Asset],
    portfolio: exchange_data_import.PortfolioDetails,
    unit: typing.Optional[str],
) -> list[protocol_models.Asset]:
    enriched: list[protocol_models.Asset] = []
    for asset in base_assets:
        update_fields: dict[str, typing.Any] = {}
        if asset.symbol in portfolio.asset_values:
            update_fields["value"] = float(portfolio.asset_values[asset.symbol])
        if unit:
            update_fields["unit"] = unit
        if update_fields:
            enriched.append(asset.model_copy(update=update_fields))
        else:
            enriched.append(asset)
    return enriched


def _order_summaries_from_open_orders(open_orders: list[dict]) -> list[protocol_models.OrderSummary]:
    order_columns = octobot_trading_enums.ExchangeConstantsOrderColumns
    summaries: list[protocol_models.OrderSummary] = []
    for order in open_orders:
        order_id = order.get(order_columns.EXCHANGE_ID.value) or order.get(order_columns.ID.value)
        symbol = order.get(order_columns.SYMBOL.value)
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
        if exchange_details.metadata.id:
            exchange_account_ids = [exchange_details.metadata.id]
    # Derive portfolio and trading summaries from automation exchange elements.
    exchange_elements = flow_automation_state.automation.exchange_account_elements
    assets: typing.Optional[list[protocol_models.Asset]] = None
    orders: typing.Optional[list[protocol_models.OrderSummary]] = None
    trades: typing.Optional[list[protocol_models.TradeSummary]] = None
    positions: typing.Optional[list[protocol_models.PositionSummary]] = None
    if exchange_elements:
        portfolio = exchange_elements.portfolio
        if portfolio.content:
            base_assets = octobot_trading_portfolios_protocol.to_protocol_assets(portfolio.content)
            unit_for_assets = exchange_details.portfolio.unit if exchange_details else None
            assets = _enrich_protocol_assets(base_assets, portfolio, unit_for_assets)
        orders = _order_summaries_from_open_orders(exchange_elements.orders.open_orders) or None
        positions = _position_summaries(exchange_elements.positions) or None
        trades = _trade_summaries(exchange_elements.trades) or None
    return protocol_automation_state.model_copy(
        update={
            "status": status,
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
