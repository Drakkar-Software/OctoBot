import mock

import octobot_flow.entities
import octobot_flow.logic.dsl
import octobot_flow.parsers.automation_state_reader as automation_state_reader
import octobot_trading.dsl


def _minimal_state_empty_dag() -> octobot_flow.entities.AutomationState:
    return octobot_flow.entities.AutomationState.from_dict({
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": []},
        },
    })


class TestGetAutomationCopiedStrategyIds:
    def test_empty_when_no_executable_actions(self):
        reader = automation_state_reader.AutomationStateReader(_minimal_state_empty_dag())
        assert reader.get_automation_copied_strategy_ids() == []

    def test_returns_unique_strategy_ids(self):
        dependency_alpha = octobot_trading.dsl.CopyTradingDependency(strategy_id="strategy_alpha", refresh_required=False)
        dependency_beta = octobot_trading.dsl.CopyTradingDependency(strategy_id="strategy_beta", refresh_required=False)
        duplicate_alpha = octobot_trading.dsl.CopyTradingDependency(strategy_id="strategy_alpha", refresh_required=False)
        with mock.patch.object(
            octobot_flow.logic.dsl,
            "get_copy_trading_dependencies",
            return_value=[dependency_alpha, dependency_beta, duplicate_alpha],
        ):
            reader = automation_state_reader.AutomationStateReader(_minimal_state_empty_dag())
            assert set(reader.get_automation_copied_strategy_ids()) == {"strategy_alpha", "strategy_beta"}

    def test_ignores_priority_actions_uses_dag_executable_only(self):
        captured_actions: list[list[octobot_flow.entities.AbstractActionDetails]] = []

        def capture_copy_dependencies(
            actions: list[octobot_flow.entities.AbstractActionDetails],
            minimal_profile_data,
        ):
            captured_actions.append(actions)
            return []

        dag_action = octobot_flow.entities.DSLScriptActionDetails(
            id="dag_action",
            dsl_script="True",
        )
        priority_action = octobot_flow.entities.DSLScriptActionDetails(
            id="priority_action",
            dsl_script="True",
        )
        state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=octobot_flow.entities.ActionsDAG(actions=[dag_action]),
            ),
            priority_actions=[priority_action],
        )
        with mock.patch.object(
            octobot_flow.logic.dsl,
            "get_copy_trading_dependencies",
            side_effect=capture_copy_dependencies,
        ):
            reader = automation_state_reader.AutomationStateReader(state)
            assert reader.get_automation_copied_strategy_ids() == []
        assert len(captured_actions) == 1
        assert len(captured_actions[0]) == 1
        assert captured_actions[0][0].id == "dag_action"


class TestGetExecutableActions:
    def test_delegates_to_dag(self):
        dag_action = octobot_flow.entities.DSLScriptActionDetails(
            id="dag_action",
            dsl_script="True",
        )
        state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=octobot_flow.entities.ActionsDAG(actions=[dag_action]),
            ),
        )
        reader = automation_state_reader.AutomationStateReader(state)
        assert reader.get_executable_actions() == state.automation.actions_dag.get_executable_actions()
