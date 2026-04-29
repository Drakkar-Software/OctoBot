#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import abc
import time
import typing

import octobot.automation.bases.automation_step as automation_step
import octobot.automation.bases.execution_details as execution_details


class AbstractTriggerEvent(automation_step.AutomationStep, abc.ABC):
    def __init__(self):
        super(AbstractTriggerEvent, self).__init__()
        self.should_stop = False
        self.trigger_only_once = False
        self.max_trigger_frequency = 0

    async def stop(self):
        self.should_stop = True

    async def _get_next_event(self) -> typing.Optional[str]:
        raise NotImplementedError

    async def next_execution(self) -> typing.AsyncGenerator[execution_details.ExecutionDetails, None]:
        """
        Async generator, use as follows:
            async for event in self.next_event():
                # triggered when an event occurs
        """
        self.last_execution_details.timestamp = 0
        while not self.should_stop and not (self.trigger_only_once and self.last_execution_details.timestamp != 0):
            event_description = await self._get_next_event()
            trigger_time = time.time()
            if not self.max_trigger_frequency or (trigger_time - self.last_execution_details.timestamp > self.max_trigger_frequency):
                self.update_last_execution_details(description=event_description)
                yield self.last_execution_details
