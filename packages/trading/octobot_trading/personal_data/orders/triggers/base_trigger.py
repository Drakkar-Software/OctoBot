#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import typing


class BaseTrigger:
    def __init__(self, on_trigger_callback: typing.Callable, on_trigger_callback_args: tuple):
        self.on_trigger_callback: typing.Callable = on_trigger_callback
        self.on_trigger_callback_args: tuple = on_trigger_callback_args

        self._trigger_event: asyncio.Event = None    # will be set when the trigger is hit
        self._trigger_task: asyncio.Task = None

    def triggers(self, *args) -> bool:
        raise NotImplementedError("triggers is not implemented")

    def triggered(self) -> bool:
        return self._trigger_event is not None and self._trigger_event.is_set()

    def is_pending(self) -> bool:
        return self._trigger_task is not None and not self._trigger_task.done()

    def update_from_other_trigger(self, other_trigger):
        raise NotImplementedError("update_from_other_trigger is not implemented")

    def update(self, **kwargs):
        raise NotImplementedError("update is not implemented")

    def __str__(self):
        return f"{self.__class__.__name__}({self.on_trigger_callback.__name__ if self.on_trigger_callback else None})"

    async def create_watcher(self, *args):
        # ensure triggers are ready
        if self._trigger_event is None:
            self._create_trigger_event(*args)
        else:
            self._trigger_event.clear()
        if self._trigger_task is None or self._trigger_task.done():
            if self._trigger_event.is_set():
                await self.call_callback()
            else:
                self._create_trigger_task()

    def clear(self):
        if self._trigger_task is not None:
            if not self._trigger_event.is_set():
                self._trigger_task.cancel()
            self._trigger_task = None
        self.on_trigger_callback = None
        self.on_trigger_callback_args = None

    def _create_trigger_event(self, *args):
        raise NotImplementedError("_create_trigger_event is not implemented")

    async def _wait_for_trigger_set(self):
        await asyncio.wait_for(self._trigger_event.wait(), timeout=None)
        await self.call_callback()

    async def call_callback(self):
        await self.on_trigger_callback(*self.on_trigger_callback_args)

    def _create_trigger_task(self):
        self._trigger_task = asyncio.create_task(self._wait_for_trigger_set())
