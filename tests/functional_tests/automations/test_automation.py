#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest
import mock

import octobot.automation
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_commons.asyncio_tools as asyncio_tools
import tests.test_utils.config as config
import tests.functional_tests.automations as test_automations


@pytest.fixture
def automation():
    import tentacles
    tentacles_manager_api.reload_tentacle_info()
    return octobot.automation.Automation("bot_id", config.load_test_tentacles_config())


@pytest.mark.asyncio
async def test_empty_initialize(automation):
    await automation.initialize()
    assert automation.automation_details == []


def test_get_all_steps(automation):
    # ensure tentacles automations are available (counts are all + 1 due to testing steps)
    all_events, all_conditions, all_actions = automation.get_all_steps()
    assert len(all_events) > 2
    assert len(all_conditions) > 1
    assert len(all_actions) > 2


@pytest.mark.asyncio
async def test_automation_workflow(automation):
    test_config = {
        automation.AUTOMATIONS_COUNT: 1,
        automation.AUTOMATIONS: {
            "1": {
                automation.TRIGGER_EVENT: test_automations.TestTriggerEvent.get_name(),
                automation.CONDITIONS: [test_automations.TestCondition.get_name()],
                automation.ACTIONS: [test_automations.TestAction.get_name()],
                test_automations.TestTriggerEvent.get_name(): {},
                test_automations.TestCondition.get_name(): {},
                test_automations.TestAction.get_name(): {},
            }
        }
    }
    with mock.patch.object(tentacles_manager_api, "get_tentacle_config", mock.Mock(return_value=test_config)) \
         as get_tentacle_config_mock:
        await automation.initialize()
        get_tentacle_config_mock.assert_called_once()

        assert len(automation.automation_details) == 1
        automation_detail = automation.automation_details[0]
        assert isinstance(automation_detail.trigger_event, test_automations.TestTriggerEvent)
        assert len(automation_detail.conditions) == 1
        assert len(automation_detail.actions) == 1
        assert isinstance(automation_detail.conditions[0], test_automations.TestCondition)
        assert isinstance(automation_detail.actions[0], test_automations.TestAction)

        automation_detail.trigger_event.get_next_event_mock.assert_not_awaited()
        automation_detail.conditions[0].evaluate_mock.assert_not_awaited()
        automation_detail.actions[0].process_mock.assert_not_awaited()

        # wait for automation task to process
        await asyncio_tools.wait_asyncio_next_cycle()

        # ensure automation went through trigger event, condition and action
        automation_detail.trigger_event.get_next_event_mock.assert_awaited_once()
        automation_detail.conditions[0].evaluate_mock.assert_awaited_once()
        automation_detail.actions[0].process_mock.assert_awaited_once()
