import octobot_flow.entities
import octobot_flow.logic.configuration
import octobot_flow.logic.dsl


class AutomationStateReader:
    def __init__(self, state: octobot_flow.entities.AutomationState):
        self.state: octobot_flow.entities.AutomationState = state

    def get_automation_copied_strategy_ids(self) -> list[str]:
        to_execute_actions = self.state.automation.actions_dag.get_executable_actions()
        self._resolve_dsl_scripts_for_actions(to_execute_actions)
        minimal_profile_data = octobot_flow.logic.configuration.create_profile_data(
            self.state.exchange_account_details,
            self.state.automation.metadata.automation_id,
            set(),
        )
        copy_trading_dependencies = octobot_flow.logic.dsl.get_copy_trading_dependencies(
            to_execute_actions, minimal_profile_data
        )
        return list(set(
            copy_trading_dependency.strategy_id
            for copy_trading_dependency in copy_trading_dependencies
        ))

    def _resolve_dsl_scripts_for_actions(
        self, actions: list[octobot_flow.entities.AbstractActionDetails]
    ) -> None:
        # Align with AutomationJob._resolve_dsl_scripts(..., from_actions_dag=True)
        self.state.automation.actions_dag.resolve_dsl_scripts(actions)

    def get_executable_actions(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        return self.state.automation.actions_dag.get_executable_actions()
