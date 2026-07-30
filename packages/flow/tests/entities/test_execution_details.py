import pytest

import octobot_flow.entities
import octobot_flow.enums


class TestExecutionDetailsCompleteExecution:
    def test_clears_degraded_state_on_successful_completion(self):
        execution = octobot_flow.entities.ExecutionDetails(
            degraded_state=octobot_flow.entities.DegradedStateDetails(
                since=100.0,
                error=octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
                reason="Insufficient funds",
            ),
            current_execution=octobot_flow.entities.TriggerDetails(triggered_at=1.0),
        )

        execution.complete_execution(next_execution_scheduled_to=200.0)

        assert execution.degraded_state.since == 0
        assert execution.degraded_state.error is None
        assert execution.degraded_state.reason is None
