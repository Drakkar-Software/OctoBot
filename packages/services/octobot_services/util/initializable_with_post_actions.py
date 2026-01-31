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

import abc


class InitializableWithPostAction:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.is_initialized = False

    # calls initialize_impl if not initialized
    async def initialize(self, *args) -> bool:
        if not self.is_initialized:
            if await self._initialize_impl(*args):
                await self._post_initialize(args)
                self.is_initialized = True
                return True
            return False
        return False

    @abc.abstractmethod
    async def _initialize_impl(self, *args) -> bool:
        raise NotImplementedError("initialize_impl not implemented")

    # Implement _post_initialize if anything specific has to be done after initialize and before start
    async def _post_initialize(self, *args) -> bool:
        return True

