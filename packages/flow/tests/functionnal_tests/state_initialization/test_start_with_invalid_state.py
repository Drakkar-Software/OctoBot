import pytest

import octobot_flow
import octobot_flow.entities
import octobot_flow.errors

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import auth_details



@pytest.mark.asyncio
async def test_multi_bots_job_start_with_invalid_empty_state(auth_details: octobot_flow.entities.UserAuthentication):
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        # AutomationJob requires at least 1 automation
        automation_state_empty = {}
        with pytest.raises(octobot_flow.errors.NoAutomationError):
            async with octobot_flow.AutomationJob(automation_state_empty, [], {}) as automation_job:
                await automation_job.run()

        with pytest.raises(octobot_flow.errors.NoAutomationError):
            async with octobot_flow.AutomationJob(automation_state_empty, [], auth_details) as automation_job:
                await automation_job.run()

    # communit auth is not used in (raising before)
    login_mock.assert_not_called()
    insert_bot_logs_mock.assert_not_called()
