import pytest
import logging
import mock

import octobot_commons.constants as common_constants
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.constants as trading_constants

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.jobs.automation_runner_job
import octobot_flow.errors

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    auth_details,
    actions_with_market_orders,
    resolved_actions,
)


ADDED_COIN_SYMBOL = "BTC"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect", 
    [
        Exception("test"),
        octobot_flow.errors.AutomationValidationError("test")
    ]
)
async def test_raising_automation_runner_job_execution(
    global_state: dict, auth_details: octobot_flow.entities.UserAuthentication, actions_with_market_orders: list[dict], side_effect: Exception
):
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
    ):
        # test with parsed global state
        automation_state = octobot_flow.entities.AutomationState.from_dict(global_state)
        automation_state.update_automation_actions(resolved_actions(actions_with_market_orders))
        with pytest.raises(type(side_effect)):
            with mock.patch.object(
                octobot_flow.jobs.automation_runner_job.AutomationRunnerJob, "run", mock.AsyncMock(side_effect=side_effect)
            ) as run_mock:
                async with octobot_flow.AutomationJob(automation_state, [], auth_details) as automations_job:
                    await automations_job.run()
                run_mock.assert_awaited_once()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_market_orders)
        for action in actions:
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at is None
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.result is None
