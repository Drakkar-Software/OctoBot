import dataclasses
import typing
import time

import octobot_commons.dsl_interpreter
import octobot_commons.dataclasses
import octobot_flow.enums
import octobot_flow.errors

@dataclasses.dataclass
class ActionDependency(octobot_commons.dataclasses.FlexibleDataclass):
    # id of the action this dependency is on
    action_id: str = dataclasses.field(repr=True)
    # value of the dependency result. Used by an action to resolve its own DSL script when it has dependencies
    parameter: typing.Optional[str] = dataclasses.field(default=None, repr=False)


@dataclasses.dataclass
class AbstractActionDetails(octobot_commons.dataclasses.FlexibleDataclass):
    # unique id of the action
    id: str = dataclasses.field(repr=True)
    # result of the action. Set after the action is executed
    result: typing.Optional[
        octobot_commons.dsl_interpreter.ComputedOperatorParameterType
    ] = dataclasses.field(default=None, repr=True)
    # error status of the action. Set after the action is executed, in case an error occured
    error_status: typing.Optional[str] = dataclasses.field(default=None, repr=True)       # ActionErrorStatus
    # time at which the action was executed
    executed_at: typing.Optional[float] = dataclasses.field(default=None, repr=True)
    # dependencies of this action. If an action has dependencies, it will not be executed until all its dependencies are completed
    dependencies: list["ActionDependency"] = dataclasses.field(default_factory=list, repr=True)
    # id of the action to reset the DAG to. If set, will reset the DAG to this action after this action is completed.
    reset_target_action_id: typing.Optional[str] = dataclasses.field(default=None, repr=False)
    # result of the previous execution of this action. Used when the action is reset
    previous_execution_result: typing.Optional[dict] = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if self.dependencies:
            self.dependencies = [
                ActionDependency.from_dict(dependency) if 
                isinstance(dependency, dict) else dependency
                for dependency in self.dependencies
            ]

    def complete(
        self,
        result: typing.Optional[dict] = None,
        error_status: typing.Optional[str] = None,
    ):
        self.executed_at = time.time()
        if result:
            self.result = result
        if error_status:
            self.error_status = error_status

    def is_completed(self) -> bool:
        return self.executed_at is not None

    def update_execution_details(self, action: "AbstractActionDetails"):
        self.result = action.result
        self.executed_at = action.executed_at
        self.error_status = action.error_status

    def should_be_historised_in_database(self) -> bool:
        return False

    def add_dependency(self, action_id: str, parameter: typing.Optional[str] = None):
        self.dependencies.append(ActionDependency(action_id, parameter))

    def get_summary(self, minimal: bool = False) -> str:
        raise NotImplementedError("get_summary is not implemented for this bot action type")

    def get_rescheduled_parameters(self) -> dict:
        rescheduled_parameters = {}
        if self.previous_execution_result:
            if octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
                self.previous_execution_result
            ):
                rescheduled_parameters[
                    octobot_commons.dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
                ] = self.previous_execution_result
        return rescheduled_parameters

    def reset(self):
        self.previous_execution_result = self.result
        self.result = None
        self.error_status = None
        self.executed_at = None


@dataclasses.dataclass
class DSLScriptActionDetails(AbstractActionDetails):
    # DSL script to execute
    dsl_script: typing.Optional[str] = dataclasses.field(default=None, repr=True) # should be set to the DSL script
    # resolved DSL script. self.dsl_script where all the dependencies have been replaced by their actual values
    resolved_dsl_script: typing.Optional[str] = dataclasses.field(default=None, repr=False) # should be set to the resolved DSL script

    def get_summary(self, minimal: bool = False) -> str:
        if minimal:
            # only return the first operator name
            return str(self.dsl_script).split("(")[0]
        return str(self.dsl_script)

    def get_resolved_dsl_script(self) -> str:
        if not self.resolved_dsl_script:
            raise octobot_flow.errors.UnresolvedDSLScriptError(f"Resolved DSL script is not set: {self.resolved_dsl_script}")
        if octobot_commons.dsl_interpreter.has_unresolved_parameters(self.resolved_dsl_script):
            raise octobot_flow.errors.UnresolvedDSLScriptError(f"Resolved DSL script has unresolved parameters: {self.resolved_dsl_script}")
        return self.resolved_dsl_script

    def clear_resolved_dsl_script(self):
        self.resolved_dsl_script = None


@dataclasses.dataclass
class ConfiguredActionDetails(AbstractActionDetails):
    # type of the action. Must be an ActionType
    action: str = dataclasses.field(default=octobot_flow.enums.ActionType.UNKNOWN.value, repr=True)
    # configuration of the action. A dict specific to the action type
    config: typing.Optional[dict] = dataclasses.field(default=None, repr=False)

    def get_summary(self, minimal: bool = False) -> str:
        return self.action


def parse_action_details(action_details: dict) -> AbstractActionDetails:
    if "dsl_script" in action_details:
        return DSLScriptActionDetails.from_dict(action_details)
    elif "action" in action_details:
        return ConfiguredActionDetails.from_dict(action_details)
    raise ValueError(f"Invalid action details: {action_details}")
