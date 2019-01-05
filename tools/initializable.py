#  Drakkar-Software OctoBot
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

from abc import *


class Initializable:

    def __init__(self):
        self.is_initialized = False

    # calls initialize_impl if not initialized
    async def initialize(self, force=False):
        if not self.is_initialized or force:
            await self.initialize_impl()
            self.is_initialized = True
            return True
        return False

    @abstractmethod
    async def initialize_impl(self):
        raise NotImplementedError("initialize_impl not implemented")

    def get_is_initialized(self):
        return self.is_initialized
