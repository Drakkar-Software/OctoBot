import pytest

import octobot_flow
import octobot_flow.entities
import octobot_flow.errors

from tests.functionnal_tests import global_state, auth_details


@pytest.mark.asyncio
async def test_not_automations_configured(global_state: dict, auth_details: octobot_flow.entities.UserAuthentication):
    global_state["automation"] = {}
    with pytest.raises(octobot_flow.errors.NoAutomationError):
        async with octobot_flow.AutomationJob(global_state, [], auth_details):
            pass
