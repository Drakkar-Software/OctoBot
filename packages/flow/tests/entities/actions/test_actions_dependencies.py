#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.
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
import pytest

import octobot_commons.constants as commons_constants

import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.entities.actions.actions_dependencies as actions_dependencies
import octobot_flow.enums as flow_enums
import octobot_flow.errors as flow_errors


def _dsl_action(action_id: str, dsl_script: str, dependencies: list[dict]) -> action_details.DSLScriptActionDetails:
    return action_details.DSLScriptActionDetails(
        id=action_id,
        dsl_script=dsl_script,
        dependencies=dependencies,
    )


def _actions_by_id(*actions: action_details.AbstractActionDetails) -> dict[str, action_details.AbstractActionDetails]:
    return {action.id: action for action in actions}


class TestActionsDependenciesResolverResolveDslScript:
    def test_merges_dynamic_dependencies_into_list(self):
        unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        strategy_action = _dsl_action(
            "action_strategy",
            f"simple_strategy_evaluator(time_frames=['1h'], _dynamic_dependencies={unresolved_placeholder})",
            [
                {"action_id": "action_init"},
                {"action_id": "action_dma", "parameter": "_dynamic_dependencies"},
                {"action_id": "action_rsi", "parameter": "_dynamic_dependencies"},
            ],
        )
        dma_action = _dsl_action("action_dma", "dma_evaluator()", [{"action_id": "action_init"}])
        rsi_action = _dsl_action("action_rsi", "rsi_evaluator()", [{"action_id": "action_init"}])
        init_action = action_details.ConfiguredActionDetails(id="action_init")
        init_action.complete(result={"done": True})
        dma_action.complete(result={"eval_note": 1, "evaluator_name": "DMA"})
        rsi_action.complete(result={"eval_note": -1, "evaluator_name": "RSI"})

        resolver = actions_dependencies.ActionsDependenciesResolver(
            _actions_by_id(init_action, dma_action, rsi_action, strategy_action)
        )
        resolver.resolve_dsl_script(strategy_action)

        assert strategy_action.resolved_dsl_script == (
            "simple_strategy_evaluator(time_frames=['1h'], "
            "_dynamic_dependencies=[{'operator_name': 'dma_evaluator', 'result': {'eval_note': 1, 'evaluator_name': 'DMA'}}, "
            "{'operator_name': 'rsi_evaluator', 'result': {'eval_note': -1, 'evaluator_name': 'RSI'}}])"
        )

    def test_resolves_dca_dynamic_dependencies_from_strategy_result(self):
        unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        dca_action = _dsl_action(
            "action_dca",
            f"dca_trading_mode(_dynamic_dependencies={unresolved_placeholder})",
            [
                {"action_id": "action_init"},
                {"action_id": "action_strategy", "parameter": "_dynamic_dependencies"},
            ],
        )
        strategy_action = _dsl_action("action_strategy", "simple_strategy_evaluator()", [{"action_id": "action_init"}])
        init_action = action_details.ConfiguredActionDetails(id="action_init")
        init_action.complete(result={"done": True})
        strategy_action.complete(result={"eval_note": 0, "evaluator_name": "SimpleStrategyEvaluator"})

        resolver = actions_dependencies.ActionsDependenciesResolver(
            _actions_by_id(init_action, strategy_action, dca_action)
        )
        resolver.resolve_dsl_script(dca_action)

        assert strategy_action.result == {"eval_note": 0, "evaluator_name": "SimpleStrategyEvaluator"}
        assert dca_action.resolved_dsl_script == (
            "dca_trading_mode(_dynamic_dependencies=["
            "{'operator_name': 'simple_strategy_evaluator', "
            "'result': {'eval_note': 0, 'evaluator_name': 'SimpleStrategyEvaluator'}}])"
        )

    def test_dynamic_dependency_fan_out_from_list_result(self):
        unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        strategy_action = _dsl_action(
            "action_strategy",
            f"simple_strategy_evaluator(time_frames=['1h'], _dynamic_dependencies={unresolved_placeholder})",
            [
                {"action_id": "action_init"},
                {"action_id": "action_dma", "parameter": "_dynamic_dependencies"},
            ],
        )
        dma_action = _dsl_action("action_dma", "dma_evaluator()", [{"action_id": "action_init"}])
        init_action = action_details.ConfiguredActionDetails(id="action_init")
        init_action.complete(result={"done": True})
        dma_action.complete(result=[
            {"eval_note": 1, "evaluator_name": "DMA", "symbol": "BTC/USDC"},
            {"eval_note": -1, "evaluator_name": "DMA", "symbol": "ETH/USDC"},
        ])

        resolver = actions_dependencies.ActionsDependenciesResolver(
            _actions_by_id(init_action, dma_action, strategy_action)
        )
        resolver.resolve_dsl_script(strategy_action)

        assert strategy_action.resolved_dsl_script == (
            "simple_strategy_evaluator(time_frames=['1h'], "
            "_dynamic_dependencies=["
            "{'operator_name': 'dma_evaluator', 'result': {'eval_note': 1, 'evaluator_name': 'DMA', 'symbol': 'BTC/USDC'}}, "
            "{'operator_name': 'dma_evaluator', 'result': {'eval_note': -1, 'evaluator_name': 'DMA', 'symbol': 'ETH/USDC'}}"
            "])"
        )


class TestActionsDependenciesResolverReadDependencyResult:
    def test_returns_scalar_result(self):
        dependency_action = action_details.DSLScriptActionDetails(
            id="action_source",
            dsl_script="dma_evaluator()",
            dependencies=[],
        )
        dependency_action.complete(result={"eval_note": 1})
        dependency = action_details.ActionDependency(
            action_id="action_source",
            parameter="exchange_order_id",
        )
        resolver = actions_dependencies.ActionsDependenciesResolver(_actions_by_id(dependency_action))
        resolved_value = resolver.read_dependency_result(dependency)
        assert resolved_value == {"eval_note": 1}

    def test_returns_list_result(self):
        dependency_action = action_details.DSLScriptActionDetails(
            id="action_source",
            dsl_script="dma_evaluator()",
            dependencies=[],
        )
        dependency_action.complete(result=[{"eval_note": 1}, {"eval_note": -1}])
        dependency = action_details.ActionDependency(
            action_id="action_source",
            parameter="_dynamic_dependencies",
        )
        resolver = actions_dependencies.ActionsDependenciesResolver(_actions_by_id(dependency_action))
        resolved_value = resolver.read_dependency_result(dependency)
        assert resolved_value == [{"eval_note": 1}, {"eval_note": -1}]

    def test_navigates_result_path(self):
        dependency_action = action_details.DSLScriptActionDetails(
            id="action_source",
            dsl_script="exchange_action()",
            dependencies=[],
        )
        dependency_action.complete(result={"nested": {"order_id": "abc-123"}})
        dependency = action_details.ActionDependency(
            action_id="action_source",
            parameter="exchange_order_id",
            result_path=["nested", "order_id"],
        )
        resolver = actions_dependencies.ActionsDependenciesResolver(_actions_by_id(dependency_action))
        resolved_value = resolver.read_dependency_result(dependency)
        assert resolved_value == "abc-123"

    def test_raises_when_dependency_action_errored(self):
        dependency_action = action_details.DSLScriptActionDetails(
            id="action_source",
            dsl_script="dma_evaluator()",
            dependencies=[],
        )
        dependency_action.complete(
            error_status=flow_enums.ActionErrorStatus.INVALID_ORDER.value,
        )
        dependency = action_details.ActionDependency(
            action_id="action_source",
            parameter="exchange_order_id",
        )
        resolver = actions_dependencies.ActionsDependenciesResolver(_actions_by_id(dependency_action))
        with pytest.raises(flow_errors.ActionDependencyError):
            resolver.read_dependency_result(dependency)


class TestActionsDependenciesResolverFilledAllDependencies:
    def test_returns_true_when_all_dependencies_completed(self):
        init_action = action_details.ConfiguredActionDetails(id="action_init")
        init_action.complete(result={"done": True})
        dependent_action = _dsl_action("action_dma", "dma_evaluator()", [{"action_id": "action_init"}])
        resolver = actions_dependencies.ActionsDependenciesResolver(
            _actions_by_id(init_action, dependent_action)
        )

        assert resolver.filled_all_dependencies(dependent_action) is True

    def test_raises_when_dependency_action_id_unknown(self):
        dependent_action = _dsl_action("action_dma", "dma_evaluator()", [{"action_id": "action_missing"}])
        resolver = actions_dependencies.ActionsDependenciesResolver(_actions_by_id(dependent_action))

        with pytest.raises(flow_errors.ActionDependencyNotFoundError):
            resolver.filled_all_dependencies(dependent_action)


class TestActionsDependenciesResolverGetTransitiveDependents:
    def test_returns_all_direct_and_indirect_dependents(self):
        init_action = action_details.ConfiguredActionDetails(id="action_init")
        dma_action = _dsl_action("action_dma", "dma_evaluator()", [{"action_id": "action_init"}])
        strategy_action = _dsl_action(
            "action_strategy",
            "simple_strategy_evaluator()",
            [{"action_id": "action_dma"}],
        )
        resolver = actions_dependencies.ActionsDependenciesResolver(
            _actions_by_id(init_action, dma_action, strategy_action)
        )

        assert resolver.get_transitive_dependents("action_init") == {"action_dma", "action_strategy"}
