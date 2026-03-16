import pytest
import logging
import re

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.errors
import octobot_flow
import octobot_flow.entities

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, global_state, auth_details, isolated_exchange_cache, resolved_actions


def index_actions():
    return [
        {
            "id": "action_1",
            "dsl_script": "IndexTradingMode('BTC/USDT')",
        }
    ]


@pytest.mark.asyncio
async def test_index_update(
    global_state: dict, auth_details: octobot_flow.entities.UserAuthentication,
    isolated_exchange_cache,  # use isolated exchange cache to avoid side effects on other tests (uses different markets)
):
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        async with octobot_flow.AutomationJob(global_state, [], auth_details) as automations_job:
            automations_job.automation_state.update_automation_actions(resolved_actions(index_actions()))
            with pytest.raises(octobot_commons.errors.UnsupportedOperatorError, match=re.escape("Unknown operator: IndexTradingMode")):
                await automations_job.run()
        return # TODO: remove this once the index update is implemented
        after_execution_dump = automations_job.dump()
        # scheduled next execution time at 1h after the current execution (1h is the default time when unspecified)
        assert after_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        assert after_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"] == (
            after_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
            + common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR] * common_constants.MINUTE_TO_SECONDS
        )
        # check portfolio content
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_execution_dump, dict)
        assert list(sorted(after_execution_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_execution_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_execution_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_execution_portfolio_content["BTC"]["available"] < 0.01
        logging.getLogger("test_update_simulated_basket_bot").info(f"after_execution_portfolio_content: {after_execution_portfolio_content}")
        # check bot logs
        login_mock.assert_called_once()
        insert_bot_logs_mock.assert_called_once()
