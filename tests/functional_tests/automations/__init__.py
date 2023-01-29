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
import mock

import octobot.automation
import octobot_commons.configuration as configuration


class TestTriggerEvent(octobot.automation.AbstractTriggerEvent):
    def __init__(self):
        super().__init__()
        self.get_next_event_mock = mock.AsyncMock()
        self.trigger_only_once = True

    async def _get_next_event(self):
        # trigger instantly
        await self.get_next_event_mock()

    @staticmethod
    def get_description() -> str:
        return ""

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        return


class TestCondition(octobot.automation.AbstractCondition):
    def __init__(self):
        super().__init__()
        self.evaluate_mock = mock.AsyncMock()

    async def evaluate(self) -> bool:
        await self.evaluate_mock()
        return True

    @staticmethod
    def get_description() -> str:
        return ""

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        return


class TestAction(octobot.automation.AbstractAction):
    def __init__(self):
        super().__init__()
        self.process_mock = mock.AsyncMock()

    async def process(self):
        # trigger instantly
        await self.process_mock()

    @staticmethod
    def get_description() -> str:
        return ""

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        return
