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
import mock

import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.entities.actions.actions_dag as actions_dag
import octobot_flow.entities.actions.actions_dependencies as actions_dependencies
import octobot_flow.enums as flow_enums


def _configured_action(action_id: str) -> action_details.ConfiguredActionDetails:
    return action_details.ConfiguredActionDetails(id=action_id)


def _apply_configuration_action(action_id: str) -> action_details.ConfiguredActionDetails:
    return action_details.ConfiguredActionDetails(
        id=action_id,
        action=flow_enums.ActionType.APPLY_CONFIGURATION.value,
    )


def _dsl_action(action_id: str, dependencies: list[dict] | None = None) -> action_details.DSLScriptActionDetails:
    return action_details.DSLScriptActionDetails(
        id=action_id,
        dsl_script="dma_evaluator()",
        dependencies=dependencies or [],
    )


class TestGetExecutableActions:
    def test_returns_action_with_no_dependencies(self):
        action = _configured_action("action_init")
        dag = actions_dag.ActionsDAG(actions=[action])

        assert dag.get_executable_actions() == [action]

    def test_excludes_action_with_incomplete_dependency(self):
        init_action = _configured_action("action_init")
        dependent_action = _dsl_action("action_dma", dependencies=[{"action_id": "action_init"}])
        dag = actions_dag.ActionsDAG(actions=[init_action, dependent_action])

        assert dag.get_executable_actions() == [init_action]

    def test_includes_action_when_all_dependencies_completed(self):
        init_action = _configured_action("action_init")
        init_action.complete(result={"done": True})
        dependent_action = _dsl_action("action_dma", dependencies=[{"action_id": "action_init"}])
        dag = actions_dag.ActionsDAG(actions=[init_action, dependent_action])

        assert dag.get_executable_actions() == [dependent_action]


class TestResetTo:
    def test_resets_transitive_dependents_but_not_apply_configuration_action(self):
        init_action = _apply_configuration_action("action_init")
        init_action.complete(result={"done": True})
        dma_action = _dsl_action("action_dma", dependencies=[{"action_id": "action_init"}])
        dma_action.complete(result={"eval_note": 1})
        strategy_action = _dsl_action("action_strategy", dependencies=[{"action_id": "action_dma"}])
        strategy_action.complete(result={"eval_note": 0})
        dag = actions_dag.ActionsDAG(actions=[init_action, dma_action, strategy_action])

        dag.reset_to("action_init")

        assert init_action.executed_at is not None
        assert dma_action.executed_at is None
        assert strategy_action.executed_at is None

    def test_resets_resettable_configured_action_and_its_dependents(self):
        init_action = _configured_action("action_init")
        init_action.complete(result={"done": True})
        dma_action = _dsl_action("action_dma", dependencies=[{"action_id": "action_init"}])
        dma_action.complete(result={"eval_note": 1})
        dag = actions_dag.ActionsDAG(actions=[init_action, dma_action])

        dag.reset_to("action_init")

        assert init_action.executed_at is None
        assert dma_action.executed_at is None

    def test_resets_dsl_action_and_its_dependents(self):
        init_action = _configured_action("action_init")
        init_action.complete(result={"done": True})
        dma_action = _dsl_action("action_dma", dependencies=[{"action_id": "action_init"}])
        dma_action.complete(result={"eval_note": 1})
        strategy_action = _dsl_action("action_strategy", dependencies=[{"action_id": "action_dma"}])
        strategy_action.complete(result={"eval_note": 0})
        dag = actions_dag.ActionsDAG(actions=[init_action, dma_action, strategy_action])

        dag.reset_to("action_dma")

        assert init_action.executed_at is not None
        assert dma_action.executed_at is None
        assert strategy_action.executed_at is None


class TestResolveDslScripts:
    def test_delegates_to_dependencies_resolver_for_dsl_actions_only(self):
        init_action = _configured_action("action_init")
        dsl_action = _dsl_action("action_dma")
        dag = actions_dag.ActionsDAG(actions=[init_action, dsl_action])

        with mock.patch.object(
            actions_dependencies.ActionsDependenciesResolver,
            "resolve_dsl_script",
        ) as mock_resolve_dsl_script:
            dag.resolve_dsl_scripts([init_action, dsl_action])

        mock_resolve_dsl_script.assert_called_once_with(dsl_action)
