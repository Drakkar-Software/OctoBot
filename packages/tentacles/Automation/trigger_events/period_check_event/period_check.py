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
import asyncio
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot.automation.bases.abstract_trigger_event as abstract_trigger_event


class PeriodicCheck(abstract_trigger_event.AbstractTriggerEvent):
    UPDATE_PERIOD = "update_period"

    def __init__(self):
        super().__init__()
        self.waiter_task = None
        self.waiting_time = None

    async def stop(self):
        await super().stop()
        if self.waiter_task is not None and not self.waiter_task.done():
            self.waiter_task.cancel()

    async def _get_next_event(self) -> typing.Optional[str]:
        if self.should_stop:
            raise StopIteration
        self.waiter_task = asyncio.create_task(asyncio.sleep(self.waiting_time))
        await self.waiter_task

    @staticmethod
    def get_description() -> str:
        return "Will trigger periodically, at the specified update period."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {
            self.UPDATE_PERIOD: UI.user_input(
                self.UPDATE_PERIOD, commons_enums.UserInputTypes.FLOAT, 300, inputs,
                title="Update period: number of seconds to wait between each update.",
                parent_input_name=step_name,
            )
        }

    def apply_config(self, config):
        self.waiting_time = config[self.UPDATE_PERIOD]
