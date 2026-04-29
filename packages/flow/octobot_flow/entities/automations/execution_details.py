import dataclasses
import time
import typing

import octobot_commons.dataclasses
import octobot_flow.enums
import octobot_flow.entities.automations.additional_actions as additional_actions_import


@dataclasses.dataclass
class TriggerDetails(octobot_commons.dataclasses.MinimizableDataclass):
    scheduled_to: float = 0
    triggered_at: float = 0
    trigger_reason: typing.Optional[str] = None
    additional_actions: additional_actions_import.AdditionalActions = dataclasses.field(default_factory=additional_actions_import.AdditionalActions)
    custom_action_ids: list[str] = dataclasses.field(default_factory=list)
    signal_ids: list[str] = dataclasses.field(default_factory=list)
    strategy_executed_at: float = 0
    was_completed: bool = False

    def __post_init__(self):
        if self.additional_actions and isinstance(self.additional_actions, dict):
            self.additional_actions = additional_actions_import.AdditionalActions.from_dict(self.additional_actions)

    def has_custom_actions_or_signals_to_fetch(self) -> bool:
        return bool(
            self.trigger_reason == octobot_flow.enums.LastTriggerReason.CUSTOM_ACTION.value
            or self.custom_action_ids
            or self.trigger_reason == octobot_flow.enums.LastTriggerReason.SIGNAL.value
            or self.signal_ids
        )

    def was_interrupted(self) -> bool:
        return not self.was_completed


@dataclasses.dataclass
class DegradedStateDetails(octobot_commons.dataclasses.MinimizableDataclass):
    since: float = 0
    reason: typing.Optional[str] = None


@dataclasses.dataclass
class ExecutionDetails(octobot_commons.dataclasses.MinimizableDataclass):
    previous_execution: TriggerDetails = dataclasses.field(default_factory=TriggerDetails)
    current_execution: TriggerDetails = dataclasses.field(default_factory=TriggerDetails)
    degraded_state: DegradedStateDetails = dataclasses.field(default_factory=DegradedStateDetails)
    execution_error: typing.Optional[str] = None

    def __post_init__(self):
        if self.previous_execution and isinstance(self.previous_execution, dict):
            self.previous_execution = TriggerDetails.from_dict(self.previous_execution)
        if self.current_execution and isinstance(self.current_execution, dict):
            self.current_execution = TriggerDetails.from_dict(self.current_execution)
        if self.degraded_state and isinstance(self.degraded_state, dict):
            self.degraded_state = DegradedStateDetails.from_dict(self.degraded_state)

    def should_fetch_custom_actions_or_signals(self) -> bool:
        return (
            self.current_execution.has_custom_actions_or_signals_to_fetch() 
            or (self.previous_execution.was_interrupted() and self.previous_execution.has_custom_actions_or_signals_to_fetch())
        )

    def start_execution(self):
        self.current_execution.triggered_at = time.time()

    def complete_execution(self, next_execution_scheduled_to: float):
        self.current_execution.was_completed = True
        self.previous_execution = self.current_execution
        self.current_execution = TriggerDetails(
            scheduled_to=next_execution_scheduled_to,
            trigger_reason=octobot_flow.enums.LastTriggerReason.SCHEDULED.value,
            additional_actions=additional_actions_import.AdditionalActions.default_iteration(),
        )
