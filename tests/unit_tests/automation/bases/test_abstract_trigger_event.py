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
import asyncio
import pytest

from octobot.automation.bases.abstract_trigger_event import AbstractTriggerEvent
from octobot.automation.bases.execution_details import ExecutionDetails


class ConcreteTriggerEvent(AbstractTriggerEvent):
    def __init__(self):
        super().__init__()
        self._events_to_emit = []

    @staticmethod
    def get_description() -> str:
        return "Concrete trigger event"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    def set_events(self, events):
        self._events_to_emit = list(events)

    async def _get_next_event(self):
        if self._events_to_emit:
            self._events_to_emit.pop(0)
        else:
            await asyncio.sleep(10)  # Block until explicitly stopped


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestAbstractTriggerEvent:
    def test_init(self):
        trigger = ConcreteTriggerEvent()
        assert trigger.should_stop is False
        assert trigger.trigger_only_once is False
        assert trigger.max_trigger_frequency == 0

    async def test_stop_sets_should_stop(self):
        trigger = ConcreteTriggerEvent()
        await trigger.stop()
        assert trigger.should_stop is True

    async def test_next_execution_yields_execution_details(self):
        trigger = ConcreteTriggerEvent()
        trigger.set_events([None, None])  # Two events to emit

        gathered = []
        async def collect():
            async for details in trigger.next_execution():
                gathered.append(details)
                if len(gathered) >= 2:
                    trigger.should_stop = True
                    break

        task = asyncio.create_task(collect())
        await asyncio.wait_for(task, timeout=2.0)

        assert len(gathered) == 2
        assert all(isinstance(d, ExecutionDetails) for d in gathered)
        assert gathered[0].timestamp > 0
        assert gathered[1].timestamp > 0

    async def test_next_execution_respects_trigger_only_once(self):
        trigger = ConcreteTriggerEvent()
        trigger.trigger_only_once = True
        trigger.set_events([None, None])

        gathered = []
        async def collect():
            async for details in trigger.next_execution():
                gathered.append(details)
                break

        task = asyncio.create_task(collect())
        await asyncio.wait_for(task, timeout=2.0)

        assert len(gathered) == 1

    async def test_next_execution_respects_should_stop(self):
        trigger = ConcreteTriggerEvent()
        trigger.set_events([None, None, None])

        gathered = []
        async def collect():
            async for details in trigger.next_execution():
                gathered.append(details)
                if len(gathered) == 1:
                    trigger.should_stop = True
                    break

        task = asyncio.create_task(collect())
        await asyncio.wait_for(task, timeout=2.0)

        assert len(gathered) == 1
