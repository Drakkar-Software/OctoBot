import typing

import octobot_commons.dsl_interpreter

import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.enums
import octobot_flow.errors


def _navigate_dict_path(root: typing.Any, path: list[str]) -> typing.Any:
    cursor = root
    for i, key in enumerate(path):
        if isinstance(cursor, dict):
            try:
                cursor = cursor[key]
            except KeyError as err:
                raise octobot_flow.errors.ActionDependencyError(
                    f"Dependency result has no path {path[: i + 1]!r} (missing key: {key} in {list(cursor)})"
                ) from err
        elif isinstance(cursor, list) and key.isdigit():
            idx = int(key)
            if idx >= len(cursor):
                raise octobot_flow.errors.ActionDependencyError(
                    f"Dependency result path {path[:i]!r} list index {idx!r} out of range (len={len(cursor)})"
                )
            cursor = cursor[idx]
        else:
            raise octobot_flow.errors.ActionDependencyError(
                f"Dependency result path {path[:i]!r} is not a dict or list (got {type(cursor).__name__}), "
                f"cannot apply segment {key!r}"
            )
    return cursor


class ActionsDependenciesResolver:
    def __init__(
        self,
        actions_by_id: dict[str, action_details.AbstractActionDetails],
    ):
        self._actions_by_id = actions_by_id

    def get_transitive_dependents(self, action_id: str) -> set[str]:
        """Return all action_ids that depend on the given action_id (directly or indirectly)."""
        return self._get_transitive_dependents(action_id, self._get_dependents_map())

    def _get_dependents_map(self) -> dict[str, set[str]]:
        """Return a map: action_id -> set of action_ids that directly depend on it."""
        dependents: dict[str, set[str]] = {
            action.id: set() for action in self._actions_by_id.values()
        }
        for action in self._actions_by_id.values():
            for dep in action.dependencies:
                dependents.setdefault(dep.action_id, set()).add(action.id)
        return dependents

    def _get_transitive_dependents(
        self, action_id: str, dependents_map: dict[str, set[str]]
    ) -> set[str]:
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

    def filled_all_dependencies(self, action: action_details.AbstractActionDetails) -> bool:
        try:
            return all(
                self._actions_by_id[dep.action_id].is_completed()
                for dep in action.dependencies
            )
        except KeyError as err:
            raise octobot_flow.errors.ActionDependencyNotFoundError(
                f"Action {action.id} has dependencies with unknown action IDs: {err}"
            ) from err

    def read_dependency_result(
        self,
        dependency: action_details.ActionDependency,
    ) -> typing.Any:
        dependency_action = self._actions_by_id[dependency.action_id]
        if dependency_action.error_status != octobot_flow.enums.ActionErrorStatus.NO_ERROR.value:
            raise octobot_flow.errors.ActionDependencyError(
                f"Dependency {dependency.parameter} returned an error: {dependency_action.error_status}"
            )
        value = dependency_action.result
        if dependency.result_path:
            value = _navigate_dict_path(value, dependency.result_path)
        return value

    def _dependency_values_for_dynamic_dependencies(
        self,
        resolved_value: typing.Any,
    ) -> list[typing.Any]:
        if isinstance(resolved_value, list):
            return resolved_value
        return [resolved_value]

    def _resolve_dynamic_dependency_value(
        self,
        dependency: action_details.ActionDependency,
    ) -> list[dict]:
        dependency_action = self._actions_by_id[dependency.action_id]
        if not isinstance(dependency_action, action_details.DSLScriptActionDetails):
            raise octobot_flow.errors.ActionDependencyError(
                f"Dynamic dependency action {dependency.action_id} must be a DSL script action"
            )
        operator_name = octobot_commons.dsl_interpreter.get_dsl_statement_operator_name(
            dependency_action.dsl_script
        )
        resolved_values = self._dependency_values_for_dynamic_dependencies(
            self.read_dependency_result(dependency)
        )
        return [
            octobot_commons.dsl_interpreter.DynamicDependency(
                operator_name=operator_name,
                result=resolved_value,
            ).to_dict(include_default_values=False)
            for resolved_value in resolved_values
        ]

    def _apply_dynamic_dependencies_resolution(
        self,
        action: action_details.DSLScriptActionDetails,
        resolved_dsl_script: str,
    ) -> tuple[str, list[action_details.ActionDependency], bool]:
        dynamic_dependencies_key = (
            octobot_commons.dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY
        )
        if not octobot_commons.dsl_interpreter.DynamicDependenciesOperatorMixin.dsl_statement_uses_dynamic_dependencies(
            resolved_dsl_script
        ):
            return resolved_dsl_script, action.dependencies, False

        dynamic_dependency_values = []
        remaining_dependencies = []
        for dependency in action.dependencies:
            if dependency.parameter == dynamic_dependencies_key:
                dynamic_dependency_values.extend(
                    self._resolve_dynamic_dependency_value(dependency)
                )
            else:
                remaining_dependencies.append(dependency)

        resolved_dynamic_dependencies = False
        if dynamic_dependency_values:
            resolved_dsl_script = octobot_commons.dsl_interpreter.apply_resolved_parameter_value(
                resolved_dsl_script,
                dynamic_dependencies_key,
                dynamic_dependency_values,
            )
            resolved_dynamic_dependencies = True
        return resolved_dsl_script, remaining_dependencies, resolved_dynamic_dependencies

    def _apply_regular_dependency_parameters(
        self,
        resolved_dsl_script: str,
        dependencies: list[action_details.ActionDependency],
        *,
        has_resolved_dynamic_dependencies: bool,
    ) -> str:
        dynamic_dependencies_key = (
            octobot_commons.dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY
        )
        uses_dynamic_dependencies = (
            octobot_commons.dsl_interpreter.DynamicDependenciesOperatorMixin
            .dsl_statement_uses_dynamic_dependencies(resolved_dsl_script)
        )
        for dependency in dependencies:
            if not dependency.parameter:
                # no parameter name: this dependency is not a parameter: it just needs to have been executed
                continue
            if (
                uses_dynamic_dependencies
                and has_resolved_dynamic_dependencies
                and dependency.parameter == dynamic_dependencies_key
            ):
                continue
            resolved_value = self.read_dependency_result(dependency)
            resolved_dsl_script = octobot_commons.dsl_interpreter.apply_resolved_parameter_value(
                resolved_dsl_script, dependency.parameter, resolved_value
            )
        return resolved_dsl_script

    def resolve_dsl_script(
        self,
        action: action_details.DSLScriptActionDetails,
    ) -> None:
        resolved_dsl_script = str(action.dsl_script)
        resolved_dsl_script, dependencies_to_resolve, has_resolved_dynamic_dependencies = (
            self._apply_dynamic_dependencies_resolution(action, resolved_dsl_script)
        )
        resolved_dsl_script = self._apply_regular_dependency_parameters(
            resolved_dsl_script,
            dependencies_to_resolve,
            has_resolved_dynamic_dependencies=has_resolved_dynamic_dependencies,
        )
        reschedule_params = action.get_rescheduled_parameters()
        for rescheduled_parameter, rescheduled_value in reschedule_params.items():
            if script_override := octobot_commons.dsl_interpreter.ReCallingOperatorResult.get_script_override(rescheduled_value):
                # the script override is the new DSL script to execute for this action call
                resolved_dsl_script = script_override
        for rescheduled_parameter, rescheduled_value in reschedule_params.items():
            operator = octobot_commons.dsl_interpreter.ReCallingOperatorResult.get_keyword(
                rescheduled_value
            )
            if not operator:
                raise octobot_flow.errors.ActionDependencyError(
                    f"Dependency {rescheduled_parameter} returned a re-calling operator result with no keyword value: {rescheduled_value}"
                )
            resolved_dsl_script = octobot_commons.dsl_interpreter.add_resolved_parameter_value(
                resolved_dsl_script, operator, rescheduled_parameter, rescheduled_value
            )
        action.resolved_dsl_script = resolved_dsl_script
