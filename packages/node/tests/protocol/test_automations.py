#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime

import octobot_commons.constants as octobot_commons_constants
import octobot_flow.entities as flow_entities
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.enums as octobot_trading_enums
import octobot_trading.exchanges.util.exchange_data as octobot_trading_exchange_data

import octobot_node.protocol.automations as automations_protocol


def _minimal_protocol_base() -> protocol_models.AutomationState:
    created = datetime.datetime(2020, 1, 2, tzinfo=datetime.UTC)
    updated = datetime.datetime(2020, 1, 3, tzinfo=datetime.UTC)
    return protocol_models.AutomationState(
        id="task-1",
        status=protocol_models.TaskStatus.PENDING,
        metadata=protocol_models.AutomationMetadata(
            name="task-name",
            description="task-description",
            created_at=created,
            updated_at=updated,
        ),
    )


def _minimal_automation_details(**overrides) -> flow_entities.AutomationDetails:
    data = {
        "metadata": {"automation_id": "automation_1"},
        "actions_dag": {"actions": []},
    }
    data.update(overrides)
    return flow_entities.AutomationDetails.from_dict(data)


class TestFillProtocolAutomationStateReturnAndMetadata:
    def test_returns_new_instance_and_preserves_metadata(self):
        flow_state = flow_entities.AutomationState(automation=_minimal_automation_details())
        base = _minimal_protocol_base()
        filled = automations_protocol._fill_protocol_automation_state(base, flow_state)
        assert filled is not base
        assert filled.metadata is base.metadata
        assert filled.metadata.name == "task-name"
        assert filled.metadata.description == "task-description"
        assert filled.metadata.created_at == base.metadata.created_at
        assert filled.metadata.updated_at == base.metadata.updated_at


class TestFillProtocolAutomationStateAutomationStatus:
    def test_failed_when_execution_error(self):
        execution = flow_entities.ExecutionDetails(execution_error="boom")
        flow_state = flow_entities.AutomationState(
            automation=_minimal_automation_details(execution=execution),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.status == protocol_models.TaskStatus.FAILED

    def test_failed_when_dag_action_error_status(self):
        action = flow_entities.ConfiguredActionDetails(
            id="a1",
            action="apply_configuration",
            error_status=flow_enums.ActionErrorStatus.INTERNAL_ERROR,
        )
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[action]),
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.status == protocol_models.TaskStatus.FAILED

    def test_completed_when_all_actions_completed(self):
        action = flow_entities.DSLScriptActionDetails(
            id="a1",
            dsl_script="True",
        )
        action.complete(result={"ok": True})
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[action]),
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.status == protocol_models.TaskStatus.COMPLETED

    def test_running_when_triggered(self):
        trigger = flow_entities.TriggerDetails(scheduled_to=1, triggered_at=2)
        execution = flow_entities.ExecutionDetails(current_execution=trigger)
        pending_action = flow_entities.DSLScriptActionDetails(id="a1", dsl_script="True")
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[pending_action]),
                execution=execution,
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.status == protocol_models.TaskStatus.RUNNING

    def test_pending_when_not_started(self):
        flow_state = flow_entities.AutomationState(
            automation=_minimal_automation_details(
                actions_dag={
                    "actions": [
                        {"id": "a1", "action": "apply_configuration", "config": {}},
                    ],
                },
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.status == protocol_models.TaskStatus.PENDING


class TestFillProtocolAutomationStateDagActions:
    def test_executable_vs_pending_per_action_status(self):
        blocked = flow_entities.ConfiguredActionDetails(
            id="blocked",
            action="apply_configuration",
            config={},
            dependencies=[flow_entities.ActionDependency("ready")],
        )
        ready = flow_entities.DSLScriptActionDetails(id="ready", dsl_script="True")
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[ready, blocked]),
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.actions is not None
        assert len(filled.actions) == 2
        by_id = {action.id: action for action in filled.actions}
        assert by_id["ready"].status == protocol_models.TaskStatus.RUNNING
        assert by_id["blocked"].status == protocol_models.TaskStatus.PENDING

    def test_dsl_and_configured_action_mapping(self):
        dsl_action = flow_entities.DSLScriptActionDetails(id="d1", dsl_script="noop()")
        cfg_action = flow_entities.ConfiguredActionDetails(
            id="c1",
            action="apply_configuration",
            config={"automation": {"metadata": {"automation_id": "x"}}},
        )
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[dsl_action, cfg_action]),
            ),
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.actions is not None
        by_id = {action.id: action for action in filled.actions}
        assert by_id["d1"].action_type == "dsl_script"
        assert by_id["d1"].dsl == "noop()"
        assert by_id["c1"].action_type == "apply_configuration"
        assert by_id["c1"].configuration is not None


class TestFillProtocolAutomationStatePriorityActions:
    def test_priority_actions_separate_and_running_when_incomplete(self):
        dag_action = flow_entities.DSLScriptActionDetails(id="dag_action", dsl_script="True")
        priority_action = flow_entities.DSLScriptActionDetails(id="priority_action", dsl_script="True")
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[dag_action]),
            ),
            priority_actions=[priority_action],
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.actions is not None
        assert len(filled.actions) == 1
        assert filled.actions[0].id == "dag_action"
        assert filled.priority_actions is not None
        assert len(filled.priority_actions) == 1
        assert filled.priority_actions[0].id == "priority_action"
        assert filled.priority_actions[0].status == protocol_models.TaskStatus.RUNNING


class TestFillProtocolAutomationStateExchanges:
    def test_exchanges_and_account_ids_from_exchange_details(self):
        exchange_details = flow_entities.ExchangeAccountDetails()
        exchange_details.metadata.id = "acc-1"
        exchange_details.metadata.name = "acc"
        exchange_details.exchange_details.internal_name = "binance"
        flow_state = flow_entities.AutomationState(
            automation=_minimal_automation_details(),
            exchange_account_details=exchange_details,
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.exchanges == ["binance"]
        assert filled.exchange_account_ids == ["acc-1"]


class TestFillProtocolAutomationStateAssetsOrdersPositionsTrades:
    def test_assets_orders_positions_trades_mapping(self):
        portfolio_content = {
            "BTC": {
                octobot_commons_constants.PORTFOLIO_AVAILABLE: 1.0,
                octobot_commons_constants.PORTFOLIO_TOTAL: 2.0,
            },
        }
        order_columns = octobot_trading_enums.ExchangeConstantsOrderColumns
        open_order = {
            order_columns.EXCHANGE_ID.value: "oid-1",
            order_columns.SYMBOL.value: "BTC/USDT",
        }
        missing_order = {
            order_columns.EXCHANGE_ID.value: "missing-1",
            order_columns.SYMBOL.value: "ETH/USDT",
        }
        position_columns = octobot_trading_enums.ExchangeConstantsPositionColumns
        position_details = octobot_trading_exchange_data.PositionDetails(
            position={
                position_columns.ID.value: "pos-1",
                position_columns.SYMBOL.value: "BTC/USDT",
            },
            contract={},
        )
        trade_dict = {
            order_columns.EXCHANGE_TRADE_ID.value: "t1",
            order_columns.SYMBOL.value: "BTC/USDT",
        }
        elements = flow_entities.ExchangeAccountElements()
        elements.portfolio.content = portfolio_content
        elements.orders.open_orders = [open_order]
        elements.orders.missing_orders = [missing_order]
        elements.positions = [position_details]
        elements.trades = [trade_dict]
        automation = _minimal_automation_details()
        automation.exchange_account_elements = elements
        exchange_details = flow_entities.ExchangeAccountDetails()
        exchange_details.metadata.id = "acc-1"
        exchange_details.metadata.name = "acc"
        exchange_details.exchange_details.internal_name = "binance"
        exchange_details.portfolio = flow_entities.ExchangeAccountPortfolio(unit="USDT")
        flow_state = flow_entities.AutomationState(
            automation=automation,
            exchange_account_details=exchange_details,
        )
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.assets is not None
        bitcoin_asset = filled.assets[0]
        assert bitcoin_asset.symbol == "BTC"
        assert bitcoin_asset.total == 2.0
        assert bitcoin_asset.available == 1.0
        assert filled.orders is not None
        assert len(filled.orders) == 1
        assert filled.orders[0].id == "oid-1"
        assert filled.positions is not None
        assert filled.positions[0].id == "pos-1"
        assert filled.trades is not None
        assert filled.trades[0].id == "t1"

    def test_assets_without_enrichment(self):
        portfolio_content = {
            "BTC": {
                octobot_commons_constants.PORTFOLIO_AVAILABLE: 1.0,
                octobot_commons_constants.PORTFOLIO_TOTAL: 2.0,
            },
        }
        elements = flow_entities.ExchangeAccountElements()
        elements.portfolio.content = portfolio_content
        automation = _minimal_automation_details()
        automation.exchange_account_elements = elements
        flow_state = flow_entities.AutomationState(automation=automation)
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.assets is not None
        assert filled.assets[0].symbol == "BTC"
        assert filled.assets[0].total == 2.0
        assert filled.assets[0].available == 1.0


class TestFillProtocolAutomationStateEmpties:
    def test_no_exchange_elements_yields_empty_protocol_lists(self):
        flow_state = flow_entities.AutomationState(automation=_minimal_automation_details())
        filled = automations_protocol._fill_protocol_automation_state(_minimal_protocol_base(), flow_state)
        assert filled.assets is None
        assert filled.orders is None
        assert filled.positions is None
        assert filled.trades is None
