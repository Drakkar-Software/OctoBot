import dataclasses

import octobot_commons.dataclasses

import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.entities.actions.actions_dependencies as actions_dependencies
import octobot_flow.errors


@dataclasses.dataclass
class ActionsDAG(octobot_commons.dataclasses.FlexibleDataclass):
    actions: list[action_details.AbstractActionDetails] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.actions = [
            action_details.parse_action_details(action) if isinstance(action, dict) else action
            for action in self.actions
        ]

    def add_action(self, action: action_details.AbstractActionDetails):
        self.actions.append(action)

    def __bool__(self) -> bool:
        return bool(self.actions)

    def get_actions_by_id(self) -> dict[str, action_details.AbstractActionDetails]:
        return {
            action.id: action for action in self.actions
        }

    def update_actions_results(self, actions: list[action_details.AbstractActionDetails]):
        actions_by_id = self.get_actions_by_id()
        for action in actions:
            actions_by_id[action.id].update_execution_details(action)

    def get_executable_actions(self) -> list[action_details.AbstractActionDetails]:
        """Return actions that can be executed: not yet executed, and either have no
        dependencies or all their dependencies have results (executed_at is set).
        """
        dependencies_resolver = actions_dependencies.ActionsDependenciesResolver(self.get_actions_by_id())
        return [
            action 
            for action in self.actions
            if not action.is_completed() and dependencies_resolver.filled_all_dependencies(action)
        ]

    def completed_all_actions(self) -> bool:
        return all(action.is_completed() for action in self.actions)

    def get_pending_actions(self) -> list[action_details.AbstractActionDetails]:
        return [
            action 
            for action in self.actions
            if not action.is_completed()
        ]

    def reset_to(self, action_id: str):
        """
        Reset the action identified by action_id and all DAG actions that depend
        directly or indirectly from this action.
        """
        actions_by_id = self.get_actions_by_id()
        if action_id not in actions_by_id:
            raise octobot_flow.errors.ActionDependencyNotFoundError(
                f"Action {action_id} not found in DAG"
            )
        dependencies_resolver = actions_dependencies.ActionsDependenciesResolver(actions_by_id)
        to_reset = dependencies_resolver.get_transitive_dependents(action_id)
        if actions_by_id[action_id].can_be_reset():
            # also reset the action itself
            to_reset.add(action_id)
        for aid in to_reset:
            actions_by_id[aid].reset()

    def resolve_dsl_scripts(
        self, actions: list[action_details.AbstractActionDetails]
    ):
        """
        Return the resolved DSL script, with all the dependencies resolved.
        If the DSL script is not set, return None.
        """
        actions_by_id = self.get_actions_by_id()
        dependencies_resolver = actions_dependencies.ActionsDependenciesResolver(actions_by_id)
        for action in actions:
            if isinstance(action, action_details.DSLScriptActionDetails):
                dependencies_resolver.resolve_dsl_script(action)

    def __repr__(self) -> str:
        return (
            f"ActionsDAG([{len(self.actions)}]: {', '.join([str(action) for action in self.actions])})"
        )
