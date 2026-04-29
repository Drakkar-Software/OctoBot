#  Drakkar-Software OctoBot-Services
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
import abc
import threading

import octobot_commons.logging as logging


class ReturningStartable:
    __metaclass__ = abc.ABCMeta

    # Override this method with the actions to perform when starting this
    # Called both by async and threaded versions of this (in a threaded new async loop for threaded versions)
    @abc.abstractmethod
    async def _async_run(self) -> bool:
        raise NotImplementedError(f"_async_run is not implemented for {self.__class__.__name__}")

    # Override this method if this has to be run in a thread using this body
    #
    # async def _inner_start(self) -> bool:
    #   threading.Thread.start(self)
    #   return True
    async def _inner_start(self) -> bool:
        return await self._async_run()

    # Always called to start this
    async def start(self) -> bool:
        try:
            return await self._inner_start()
        except Exception as e:
            class_name = self.__class__.__name__
            logger = logging.get_logger(class_name)
            logger.exception(e, True, f"{class_name} start error: {e}")
            return False

    def get_name(self):
        raise NotImplementedError

    def threaded_start(self):
        threading.Thread(target=self.run, name=self.get_name()).start()
        return True

    # Called by threading.Thread.start(self) when a this is threaded
    def run(self) -> None:
        asyncio.run(self._async_run())
