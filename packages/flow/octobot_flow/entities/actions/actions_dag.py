import dataclasses

import octobot_commons.dsl_interpreter
import octobot_commons.dataclasses


import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.enums
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
        return [
            action 
            for action in self.actions
            if not action.is_completed() and self.filled_all_dependencies(action)
        ]

    def completed_all_actions(self) -> bool:
        return all(action.is_completed() for action in self.actions)

    def get_pending_actions(self) -> list[action_details.AbstractActionDetails]:
        return [
            action 
            for action in self.actions
            if not action.is_completed()
        ]

    def _get_dependents_map(self) -> dict[str, set[str]]:
        """Return a map: action_id -> set of action_ids that directly depend on it."""
        dependents: dict[str, set[str]] = {action.id: set() for action in self.actions}
        for action in self.actions:
            for dep in action.dependencies:
                dependents.setdefault(dep.action_id, set()).add(action.id)
        return dependents

    def _get_transitive_dependents(self, action_id: str, dependents_map: dict[str, set[str]]) -> set[str]:
        """Return all action_ids that depend on the given action_id (directly or indirectly)."""
        result: set[str] = set()
        to_visit = [action_id]
        visited: set[str] = set()
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            for dependent_id in dependents_map.get(current, set()):
                if dependent_id not in visited:
                    result.add(dependent_id)
                    to_visit.append(dependent_id)
        return result

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
        dependents_map = self._get_dependents_map()
        to_reset = self._get_transitive_dependents(action_id, dependents_map) | {action_id}
        for aid in to_reset:
            actions_by_id[aid].reset()

    def filled_all_dependencies(self, action: action_details.AbstractActionDetails) -> bool:
        try:
            actions_by_id = self.get_actions_by_id()
            return all(
                actions_by_id[dep.action_id].is_completed()
                for dep in action.dependencies
            )
        except KeyError as err:
            raise octobot_flow.errors.ActionDependencyNotFoundError(
                f"Action {action.id} has dependencies with unknown action IDs: {err}"
            ) from err

    def resolve_dsl_scripts(
        self, actions: list[action_details.AbstractActionDetails]
    ):
        """
        Return the resolved DSL script, with all the dependencies resolved.
        If the DSL script is not set, return None.
        """
        actions_by_id = self.get_actions_by_id()
        for action in actions:
            if isinstance(action, action_details.DSLScriptActionDetails):
                self._resolve_dsl_script(action, actions_by_id)

    def _resolve_dsl_script(
        self,
        action: action_details.DSLScriptActionDetails,
        actions_by_id: dict[str, action_details.AbstractActionDetails]
    ):
        resolved_dsl_script = str(action.dsl_script)
        for dependency in action.dependencies:
            dependency_action = actions_by_id[dependency.action_id]
            if dependency_action.error_status != octobot_flow.enums.ActionErrorStatus.NO_ERROR.value:
                raise octobot_flow.errors.ActionDependencyError(
                    f"Dependency {dependency.parameter} returned an error: {dependency_action.error_status}"
                )
            if not dependency.parameter:
                # no parameter name: this dependency is not a parameter: it just needs to have been executed
                continue
            resolved_dsl_script = octobot_commons.dsl_interpreter.apply_resolved_parameter_value(
                resolved_dsl_script, dependency.parameter, dependency_action.result
            )
        for rescheduled_parameter, rescheduled_value in action.get_rescheduled_parameters().items():
            resolved_dsl_script = octobot_commons.dsl_interpreter.add_resolved_parameter_value(
                resolved_dsl_script, rescheduled_parameter, rescheduled_value
            )
        action.resolved_dsl_script = resolved_dsl_script

    def __repr__(self) -> str:
        return (
            f"ActionsDAG([{len(self.actions)}]: {', '.join([str(action) for action in self.actions])})"
        )
